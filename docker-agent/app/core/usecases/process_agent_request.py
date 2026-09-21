import logging
import asyncio
import re
import time
from contextvars import ContextVar
from contextlib import contextmanager
from typing import Any, Iterator

from app.api.schemas.contract_v1 import AgentRequestV1
from app.config import Settings
from app.core.domain.part_code import (
    has_literal_part_code_evidence,
    normalize_part_code_candidate,
)
from app.core.domain.errors import (
    PreSearchServiceUnavailableError,
    SearchPartsServiceUnavailableError,
)
from app.core.domain.models import (
    ConversationState,
    HandoffInfo,
    ItemSearchResult,
    ProcessResult,
    ResultCandidateState,
    ResultDisambiguationState,
    ToolTrace,
)
from app.core.domain.pre_search import NextQuestion, PreSearchValidation, SearchCriteria
from app.core.domain.result_disambiguation import (
    DIRECT_RESULTS_LIMIT,
    RESULT_DISAMBIGUATION_SLOT,
    build_result_disambiguation_state,
    resolve_result_disambiguation,
)
from app.core.domain.rules import validate_message_text, validate_schema_version
from app.core.ports.pre_search_review_recorder import PreSearchReviewRecorderPort
from app.core.ports.pre_search_validator import PreSearchValidatorPort
from app.core.ports.tools import ToolsPort
from app.infra.pre_search_text import normalize_pre_search_text

UNSUPPORTED_PART_HANDOFF_PROMPT = (
    "Essa familia de peca nao esta no catalogo para pesquisa automatica. "
    "Vou encaminhar para atendimento humano."
)

# A response to result disambiguation may legitimately select an attribute that
# was absent from the original criteria.  It becomes a correction only when it
# replaces a criterion that was already used to obtain the current candidates.
RESULT_DISAMBIGUATION_FILTER_FIELDS = (
    "part_code",
    "preferred_product_brand",
    "vehicle_brand",
    "vehicle_model",
    "vehicle_year",
    "engine",
    "side",
    "position",
    "axle",
    "variant",
)


class _StageTimer:
    def __init__(self) -> None:
        self._started_at = time.perf_counter()
        self._stage_latency_ms: dict[str, float] = {}

    @contextmanager
    def measure(self, stage_name: str) -> Iterator[None]:
        started_at = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            self._stage_latency_ms[stage_name] = (
                self._stage_latency_ms.get(stage_name, 0.0) + elapsed_ms
            )

    def build_tool_trace(
        self,
        *,
        used_tools: list[str],
        pre_search_path: str,
    ) -> ToolTrace:
        return ToolTrace(
            used_tools=list(used_tools),
            latency_ms=round((time.perf_counter() - self._started_at) * 1000, 2),
            stage_latency_ms={
                key: round(value, 2)
                for key, value in self._stage_latency_ms.items()
            },
            pre_search_path=pre_search_path,
        )


class ProcessAgentRequestUseCase:
    def __init__(
        self,
        *,
        tools: ToolsPort,
        pre_search_validator: PreSearchValidatorPort,
        settings: Settings,
        logger: logging.Logger,
        review_recorder: PreSearchReviewRecorderPort,
    ) -> None:
        self._tools = tools
        self._pre_search_validator = pre_search_validator
        self._settings = settings
        self._logger = logger
        self._review_recorder = review_recorder
        self._llm_semaphore = asyncio.Semaphore(
            max(1, settings.llm_max_concurrent_requests)
        )
        self._erp_search_semaphore = asyncio.Semaphore(
            max(1, settings.erp_search_max_concurrent_requests)
        )
        self._request_audit_info: ContextVar[dict[str, Any]] = ContextVar(
            "request_audit_info",
            default={},
        )

    async def execute(self, payload: AgentRequestV1) -> ProcessResult:
        self._request_audit_info.set({})
        validate_schema_version(payload.schema_version)
        query = validate_message_text(payload.message.text)
        last_messages: list[dict[str, str]] = []
        incoming_state: ConversationState | None = None
        if payload.context:
            last_messages = [
                {"role": message.role, "text": message.text}
                for message in payload.context.last_messages
            ]
            incoming_state = payload.context.conversation_state

        timing = _StageTimer()
        incoming_state, criteria_corrected = (
            self._invalidate_result_disambiguation_for_criteria_correction(
                query=query,
                incoming_state=incoming_state,
            )
        )
        if criteria_corrected:
            # The state below retains only the part family and prior fields as
            # fallback.  Keeping the old messages would let the extractor
            # reintroduce the vehicle that the customer has just corrected.
            last_messages = []
        disambiguation_result, restart_conversation = await self._try_result_disambiguation(
            payload=payload,
            query=query,
            incoming_state=incoming_state,
            timing=timing,
        )
        if disambiguation_result is not None:
            return disambiguation_result
        if restart_conversation:
            incoming_state = None
            last_messages = []

        active_item_negation = await self._try_active_item_negation(
            payload=payload,
            query=query,
            incoming_state=incoming_state,
            timing=timing,
        )
        if active_item_negation is not None:
            return active_item_negation

        with timing.measure("pre_search_validator"):
            pre_search, pre_search_path, used_tools = await self._validate_pre_search(
                query=query,
                last_messages=last_messages,
                incoming_state=incoming_state,
            )
            pre_search = self._preserve_search_continuation_criteria(
                pre_search,
                incoming_state=incoming_state,
            )
            pre_search = self._enforce_part_code_provenance(
                pre_search,
                message_text=query,
                last_messages=last_messages,
            )
            pre_search = self._canonicalize_validated_part_query(pre_search)

        with timing.measure("response_assembly"):
            actions: list[dict[str, object]] = []
            state_items = self._extract_state_items(
                query=query,
                criteria=pre_search.criteria,
                incoming_state=incoming_state,
            )
            if pre_search.items and len(pre_search.items) > 1:
                state_items = list(pre_search.items)
            state_items = self._apply_active_item_follow_up(
                items=state_items,
                criteria=pre_search.criteria,
                incoming_state=incoming_state,
            )
            item_gates = await self._validate_items_for_search(
                items=state_items,
                message_text=query,
                last_messages=last_messages,
            )
            if item_gates:
                state_items = [item_gate.criteria for item_gate in item_gates]
                searchable_items = [
                    item_gate for item_gate in item_gates if item_gate.decision == "search"
                ]
                if pre_search.decision != "handoff" and not searchable_items:
                    pre_search = item_gates[0]
                elif searchable_items:
                    actions = []
            else:
                searchable_items = []
            active_item_index = self._first_incomplete_item_index(item_gates)
            state_criteria = pre_search.criteria
            state_decision = pre_search.decision
            state_next_question = pre_search.next_question
            if active_item_index is not None:
                active_gate = item_gates[active_item_index]
                state_criteria = active_gate.criteria
                state_decision = "ask"
                state_next_question = active_gate.next_question
                if active_gate.next_question is not None and pre_search.decision != "ask":
                    actions.append(active_gate.next_question.model_dump(exclude_none=True))
            current_state = self._build_conversation_state(
                criteria=state_criteria,
                last_decision=state_decision,
                next_question=state_next_question,
                items=state_items,
                active_item_index=active_item_index,
            )
            handoff = HandoffInfo(required=False, reason=None)
            confidence = 0.0
            if pre_search.decision == "ask" and pre_search.next_question:
                actions.append(pre_search.next_question.model_dump(exclude_none=True))

        if pre_search.decision == "ask":
            with timing.measure("response_assembly"):
                reply_text = (
                    pre_search.next_question.prompt
                    if pre_search.next_question
                    else "Preciso de mais detalhes para pesquisar."
                )
                confidence = pre_search.confidence
            tool_trace = timing.build_tool_trace(
                used_tools=used_tools,
                pre_search_path=pre_search_path,
            )

            self._logger.info(
                "pre_search_validation_pending",
                extra={
                    "trace_id": payload.trace_id,
                    "conversation_id": payload.conversation_id,
                    "branch_id": payload.business.branch_id,
                    "missing_fields": pre_search.missing_fields,
                    "used_tools": used_tools,
                    "latency_ms": tool_trace.latency_ms,
                    "stage_latency_ms": tool_trace.stage_latency_ms,
                    "pre_search_path": pre_search_path,
                },
            )
            result = ProcessResult(
                reply_text=reply_text,
                actions=actions,
                handoff=handoff,
                confidence=confidence,
                tool_trace=tool_trace,
                conversation_state=current_state,
            )
            await self._record_review_case(
                payload=payload,
                last_messages=last_messages,
                pre_search=pre_search,
                result=result,
                search_query=None,
            )
            return result

        if pre_search.decision == "handoff":
            with timing.measure("response_assembly"):
                reply_text = (
                    pre_search.next_question.prompt
                    if pre_search.next_question
                    else "Nao consegui validar os dados para pesquisa automatica."
                )
                handoff = HandoffInfo(required=True, reason="pre_search_handoff")
                confidence = pre_search.confidence
            tool_trace = timing.build_tool_trace(
                used_tools=used_tools,
                pre_search_path=pre_search_path,
            )
            result = ProcessResult(
                reply_text=reply_text,
                actions=actions,
                handoff=handoff,
                confidence=confidence,
                tool_trace=tool_trace,
                conversation_state=current_state,
            )
            await self._record_review_case(
                payload=payload,
                last_messages=last_messages,
                pre_search=pre_search,
                result=result,
                search_query=None,
            )
            return result

        with timing.measure("response_assembly"):
            search_query = self._build_search_query(pre_search.criteria)
        if not search_query.strip():
            with timing.measure("response_assembly"):
                reply_text = "Preciso de mais detalhes para iniciar a pesquisa."
            tool_trace = timing.build_tool_trace(
                used_tools=used_tools,
                pre_search_path=pre_search_path,
            )
            result = ProcessResult(
                reply_text=reply_text,
                actions=actions,
                handoff=HandoffInfo(required=False, reason=None),
                confidence=max(pre_search.confidence, 0.4),
                tool_trace=tool_trace,
                conversation_state=current_state,
            )
            await self._record_review_case(
                payload=payload,
                last_messages=last_messages,
                pre_search=pre_search,
                result=result,
                search_query=search_query,
            )
            return result

        item_criteria = state_items or [pre_search.criteria]
        item_results: list[ItemSearchResult] = []
        with timing.measure("search_parts"):
            for item_index, item_criteria_row in enumerate(item_criteria):
                item_gate = item_gates[item_index] if item_gates else None
                if item_gate is not None and item_gate.decision != "search":
                    item_results.append(ItemSearchResult(
                        item=item_gate.criteria,
                        status="incomplete",
                        missing_fields=list(item_gate.missing_fields),
                    ))
                    continue
                retained_result = self._retained_item_result(
                    item_index=item_index,
                    incoming_state=incoming_state,
                )
                if retained_result is not None:
                    item_results.append(retained_result.model_copy(update={"item": item_criteria_row}))
                    continue
                item_query = self._build_search_query(item_criteria_row)
                if not item_query.strip():
                    item_results.append(ItemSearchResult(item=item_criteria_row, status="incomplete"))
                    continue
                used_tools.append("search_parts")
                try:
                    found_items = await self._search_parts(
                        query=item_query,
                        branch_id=payload.business.branch_id,
                        criteria=item_criteria_row,
                    )
                    item_results.append(ItemSearchResult(
                        item=item_criteria_row,
                        status="found" if found_items else "not_found",
                        products=found_items,
                    ))
                except SearchPartsServiceUnavailableError as exc:
                    if len(item_criteria) == 1:
                        raise
                    self._logger.warning(
                        "multi_item_search_unavailable",
                        extra={
                            "item_index": item_index,
                            "query": item_query,
                            "error_type": exc.__class__.__name__,
                        },
                    )
                    item_results.append(ItemSearchResult(
                        item=item_criteria_row, status="error", error_message=str(exc)
                    ))
                except Exception as exc:
                    self._logger.exception("multi_item_search_failed")
                    item_results.append(ItemSearchResult(
                        item=item_criteria_row, status="error", error_message=str(exc)
                    ))
        # Keep the legacy single-result flow below for one item.
        items = item_results[0].products if len(item_results) == 1 else []

        with timing.measure("response_assembly"):
            if len(item_results) > 1:
                lines = [f"Analisei {len(item_results)} pecas solicitadas:"]
                for index, result_row in enumerate(item_results, start=1):
                    label = result_row.item.part_query or "peca nao identificada"
                    quantity = (
                        f" ({result_row.item.quantity} unidade(s))"
                        if result_row.item.quantity is not None else ""
                    )
                    if result_row.status == "found":
                        lines.append(f"{index}. {label}{quantity}: {len(result_row.products)} resultado(s) encontrado(s).")
                    elif result_row.status == "not_found":
                        lines.append(f"{index}. {label}{quantity}: nenhum item encontrado no ERP.")
                    elif result_row.status == "incomplete":
                        lines.append(f"{index}. {label}{quantity}: faltam dados para pesquisar.")
                    else:
                        lines.append(f"{index}. {label}{quantity}: falha ao pesquisar; tente novamente ou solicite atendimento humano.")
                reply_text = "\n".join(lines)
                confidence = 0.85 if all(row.status != "error" for row in item_results) else 0.55
            elif len(items) == 0:
                reply_text, pending_slot, pending_question = self._build_no_match_reply(
                    criteria=pre_search.criteria,
                    missing_fields=pre_search.missing_fields,
                    incoming_state=incoming_state,
                )
                handoff = HandoffInfo(required=False, reason=None)
                current_state = self._build_conversation_state(
                    criteria=pre_search.criteria,
                    last_decision="no_match",
                    pending_slot=pending_slot,
                    pending_question=pending_question,
                    items=state_items,
                )
                confidence = 0.35
            elif len(items) == 1:
                item = items[0]
                reply_text = (
                    f"Encontrei {item.title} (codigo {item.item_id}). "
                    "Preço e estoque na filial precisam ser confirmados."
                )
                confidence = 0.93
            elif len(items) <= DIRECT_RESULTS_LIMIT:
                reply_text, list_action = self._present_catalog_items(
                    items,
                    preferred_product_brand=pre_search.criteria.preferred_product_brand,
                )
                actions = [list_action]
                confidence = 0.85
            else:
                known_fields = [
                    field for field in ("engine", "variant", "side", "position")
                    if getattr(pre_search.criteria, field, None)
                ]
                if pre_search.criteria.vehicle_model and pre_search.criteria.vehicle_year:
                    known_fields.append("application")
                disambiguation = build_result_disambiguation_state(
                    items, asked_fields=known_fields,
                )
                reply_text = disambiguation.prompt
                actions = self._result_disambiguation_actions(disambiguation)
                current_state = ConversationState(
                    criteria=pre_search.criteria,
                    items=state_items,
                    last_decision="ask",
                    pending_slot=RESULT_DISAMBIGUATION_SLOT,
                    pending_question=disambiguation.prompt,
                    result_disambiguation=disambiguation,
                )
                confidence = 0.82

            locale = self._settings.default_locale
            timezone = self._settings.default_timezone
            if payload.runtime and payload.runtime.locale:
                locale = payload.runtime.locale
            if payload.runtime and payload.runtime.timezone:
                timezone = payload.runtime.timezone

            if len(item_results) > 1:
                current_state.item_results = item_results

        tool_trace = timing.build_tool_trace(
            used_tools=used_tools,
            pre_search_path=pre_search_path,
        )

        self._logger.info(
            "tool_search_parts_finished",
            extra={
                "trace_id": payload.trace_id,
                "conversation_id": payload.conversation_id,
                "branch_id": payload.business.branch_id,
                "results_count": sum(len(row.products) for row in item_results),
                "item_search_statuses": [row.status for row in item_results],
                "item_search_errors": [
                    {
                        "item_index": index,
                        "message": row.error_message,
                    }
                    for index, row in enumerate(item_results)
                    if row.status == "error"
                ],
                "used_tools": used_tools,
                "latency_ms": tool_trace.latency_ms,
                "stage_latency_ms": tool_trace.stage_latency_ms,
                "pre_search_path": pre_search_path,
                "locale": locale,
                "timezone": timezone,
            },
        )

        result = ProcessResult(
            reply_text=reply_text,
            actions=actions,
            handoff=handoff,
            confidence=confidence,
            tool_trace=tool_trace,
            conversation_state=current_state,
            item_results=item_results if len(item_results) > 1 else None,
        )
        await self._record_review_case(
            payload=payload,
            last_messages=last_messages,
            pre_search=pre_search,
            result=result,
            search_query=search_query,
        )
        return result

    async def _try_result_disambiguation(
        self,
        *,
        payload: AgentRequestV1,
        query: str,
        incoming_state: ConversationState | None,
        timing: _StageTimer,
    ) -> tuple[ProcessResult | None, bool]:
        if (
            incoming_state is None
            or incoming_state.pending_slot != RESULT_DISAMBIGUATION_SLOT
            or incoming_state.result_disambiguation is None
        ):
            return None, False

        if self._is_result_disambiguation_subject_change(
            query=query,
            incoming_state=incoming_state,
        ):
            return None, True

        with timing.measure("response_assembly"):
            resolution = resolve_result_disambiguation(
                query,
                incoming_state.result_disambiguation,
            )
            handoff = HandoffInfo(required=False, reason=None)
            actions: list[dict[str, object]] = []
            criteria = incoming_state.criteria
            next_question: NextQuestion | None = None

            if resolution.kind == "selected" and resolution.selected_candidate is not None:
                selected = resolution.selected_candidate
                reply_text = (
                    f"Voce selecionou {selected.title} (codigo {selected.item_id}). "
                    "Confirme o codigo antes de finalizar o atendimento."
                )
                actions = [self._selected_candidate_action(selected)]
                current_state = ConversationState(
                    criteria=criteria,
                    last_decision="search",
                )
                decision = "search"
                missing_fields: list[str] = []
                confidence = 0.96
            elif resolution.kind == "listed":
                reply_text, list_action = self._present_catalog_items(
                    resolution.listed_candidates,
                    preferred_product_brand=criteria.preferred_product_brand,
                )
                actions = [list_action]
                current_state = ConversationState(criteria=criteria, last_decision="search")
                decision = "search"
                missing_fields = []
                confidence = 0.85
            elif resolution.kind in {"ask", "unresolved"} and resolution.state is not None:
                disambiguation = resolution.state
                reply_text = disambiguation.prompt
                if resolution.kind == "unresolved":
                    reply_text = f"Nao consegui identificar a opcao. {reply_text}"
                actions = self._result_disambiguation_actions(disambiguation)
                action = actions[-1]
                next_question = NextQuestion(
                    key=RESULT_DISAMBIGUATION_SLOT,
                    prompt=reply_text,
                    options=list(action.get("options") or []),
                )
                current_state = ConversationState(
                    criteria=criteria,
                    pending_slot=RESULT_DISAMBIGUATION_SLOT,
                    pending_question=reply_text,
                    last_decision="ask",
                    result_disambiguation=disambiguation,
                )
                decision = "ask"
                missing_fields = [RESULT_DISAMBIGUATION_SLOT]
                confidence = 0.78
            elif resolution.kind == "rejected":
                reply_text = (
                    "Tudo bem. Informe um novo criterio para refazer a pesquisa "
                    "ou peca atendimento humano."
                )
                current_state = ConversationState(
                    criteria=criteria,
                    pending_slot="no_match_retry",
                    pending_question=reply_text,
                    last_decision="no_match",
                )
                decision = "ask"
                missing_fields = []
                confidence = 0.55
            else:
                reply_text = (
                    "Nao consegui refinar os itens com seguranca apos tres tentativas. "
                    "Vou encaminhar para atendimento humano."
                )
                if resolution.handoff_reason == "result_disambiguation_requested":
                    reply_text = "Vou encaminhar para atendimento humano."
                handoff = HandoffInfo(
                    required=True,
                    reason=(
                        resolution.handoff_reason
                        or "result_disambiguation_limit"
                    ),
                )
                current_state = ConversationState(
                    criteria=criteria,
                    last_decision="handoff",
                )
                decision = "handoff"
                missing_fields = []
                confidence = 0.4

        tool_trace = timing.build_tool_trace(
            used_tools=["result_disambiguation"],
            pre_search_path="result_disambiguation",
        )
        result = ProcessResult(
            reply_text=reply_text,
            actions=actions,
            handoff=handoff,
            confidence=confidence,
            tool_trace=tool_trace,
            conversation_state=current_state,
        )
        synthetic_validation = PreSearchValidation(
            decision=decision,
            criteria=criteria,
            missing_fields=missing_fields,
            next_question=next_question,
            confidence=confidence,
        )
        await self._record_review_case(
            payload=payload,
            last_messages=[],
            pre_search=synthetic_validation,
            result=result,
            search_query=None,
            include_validator_audit=False,
        )
        return result, False

    async def _try_active_item_negation(
        self,
        *,
        payload: AgentRequestV1,
        query: str,
        incoming_state: ConversationState | None,
        timing: _StageTimer,
    ) -> ProcessResult | None:
        """Remove only the active item when the customer explicitly declines it."""
        if not incoming_state or incoming_state.active_item_index is None:
            return None
        items = list(incoming_state.items or [])
        index = incoming_state.active_item_index
        if index < 0 or index >= len(items):
            return None
        active_item = items[index]
        active_part = str(active_item.part_query or "").strip().casefold()
        singular_part = active_part.rstrip("s")
        normalized_query = str(query or "").casefold()
        has_negation = bool(
            re.search(r"\bn(?:a|\u00e3)o\s+(?:quero|preciso|procuro|busco)\b", normalized_query)
        )
        if not has_negation or not singular_part or singular_part not in normalized_query:
            return None

        del items[index]
        previous_results = list(incoming_state.item_results or [])
        if index < len(previous_results):
            del previous_results[index]
        remaining_criteria = items[0] if items else SearchCriteria()
        state = ConversationState(
            criteria=remaining_criteria,
            items=items or None,
            item_results=previous_results or None,
            last_decision="search" if items else "ask",
        )
        label = active_item.part_query or "a peca pendente"
        result = ProcessResult(
            reply_text=f"Certo, removi {label} desta pesquisa.",
            actions=[],
            handoff=HandoffInfo(required=False, reason=None),
            confidence=0.99,
            tool_trace=timing.build_tool_trace(
                used_tools=[],
                pre_search_path="multi_item_negation",
            ),
            conversation_state=state,
            item_results=previous_results or None,
        )
        await self._record_review_case(
            payload=payload,
            last_messages=[],
            pre_search=PreSearchValidation(
                decision="search" if items else "ask",
                criteria=remaining_criteria,
                missing_fields=[] if items else ["part_query"],
                confidence=0.99,
            ),
            result=result,
            search_query=None,
            include_validator_audit=False,
        )
        return result

    def _is_result_disambiguation_subject_change(
        self,
        *,
        query: str,
        incoming_state: ConversationState,
    ) -> bool:
        normalized = " ".join(query.strip().casefold().split())
        if any(
            marker in normalized
            for marker in ("mudando de assunto", "outra peca", "tambem preciso", "agora quero")
        ):
            return True

        extractor = getattr(
            self._pre_search_validator,
            "extract_dictionary_seed_criteria",
            None,
        )
        if not callable(extractor):
            return False
        try:
            extracted = extractor(message_text=query, last_messages=[])
        except Exception:
            return False
        current_part = str(getattr(extracted, "part_query", None) or "").strip().casefold()
        previous_part = str(incoming_state.criteria.part_query or "").strip().casefold()
        return bool(current_part and previous_part and current_part != previous_part)

    def _invalidate_result_disambiguation_for_criteria_correction(
        self,
        *,
        query: str,
        incoming_state: ConversationState | None,
    ) -> tuple[ConversationState | None, bool]:
        """Discard result candidates when the customer replaces an old filter.

        Result-disambiguation candidates are valid only for the exact criteria
        that produced them.  A new value for an already specified model, year,
        engine, side or another search filter starts a fresh validation/search;
        it must never be interpreted as an option selection from the old list.
        """
        if (
            incoming_state is None
            or incoming_state.pending_slot != RESULT_DISAMBIGUATION_SLOT
            or incoming_state.result_disambiguation is None
        ):
            return incoming_state, False

        extractor = getattr(
            self._pre_search_validator,
            "extract_dictionary_seed_criteria",
            None,
        )
        if not callable(extractor):
            return incoming_state, False
        try:
            current_criteria = extractor(message_text=query, last_messages=[])
        except Exception:
            return incoming_state, False

        previous_values = incoming_state.criteria.model_dump(exclude_none=False)
        current_values = current_criteria.model_dump(exclude_none=False)
        offered_resolution = resolve_result_disambiguation(
            query, incoming_state.result_disambiguation
        )
        is_option_answer = offered_resolution.kind in {"selected", "listed", "ask"}
        changed_fields = [
            field_name
            for field_name in RESULT_DISAMBIGUATION_FILTER_FIELDS
            if self._has_replaced_criteria_value(
                previous_values.get(field_name),
                current_values.get(field_name),
            )
            or (
                not is_option_answer
                and previous_values.get(field_name) in (None, "", [])
                and current_values.get(field_name) not in (None, "", [])
            )
        ]
        if not changed_fields:
            return incoming_state, False

        # Keep the old criteria solely so the validator can recover an omitted
        # family ("corrigindo, o carro e um Corsa...").  The corrected values
        # from the current message win during validation.  Candidates, items
        # and cached item results are intentionally not carried forward.
        return (
            ConversationState(
                criteria=incoming_state.criteria,
                pending_slot=changed_fields[0],
                last_decision="ask",
            ),
            True,
        )

    @staticmethod
    def _has_replaced_criteria_value(previous_value: object, current_value: object) -> bool:
        if previous_value in (None, "", []):
            return False
        if current_value in (None, "", []):
            return False
        if isinstance(previous_value, str) and isinstance(current_value, str):
            return previous_value.strip().casefold() != current_value.strip().casefold()
        return previous_value != current_value

    @staticmethod
    def _result_disambiguation_action(
        state: ResultDisambiguationState,
    ) -> dict[str, object]:
        if state.question_key == "item":
            options = ["Informar outro criterio", "Atendimento humano"]
            if len(state.candidates) > len(state.visible_candidate_ids):
                options.insert(0, "Ver mais")
        else:
            options = [
                f"{index} - {option.label}"
                for index, option in enumerate(state.options, start=1)
            ]
            options.append("Nenhuma dessas")
        return {
            "type": "request_info",
            "key": RESULT_DISAMBIGUATION_SLOT,
            "prompt": state.prompt,
            "options": options,
        }

    @staticmethod
    def _result_disambiguation_actions(
        state: ResultDisambiguationState,
    ) -> list[dict[str, object]]:
        actions: list[dict[str, object]] = []
        if state.question_key == "item":
            visible_ids = set(state.visible_candidate_ids)
            visible = [
                candidate for candidate in state.candidates
                if candidate.item_id in visible_ids
            ]
            actions.append(ProcessAgentRequestUseCase._catalog_items_action(visible))
        actions.append(ProcessAgentRequestUseCase._result_disambiguation_action(state))
        return actions

    @staticmethod
    def _catalog_items_action(items) -> dict[str, object]:
        return {
            "type": "show_items",
            "items": [
                {"item_id": item.item_id, "title": item.title, "score": item.score}
                for item in items
            ],
        }

    @staticmethod
    def _present_catalog_items(items, *, preferred_product_brand: str | None = None):
        text = f"Encontrei {len(items)} opções compatíveis no catálogo."
        preferred = normalize_pre_search_text(preferred_product_brand or "")
        if preferred and not any(
            preferred in normalize_pre_search_text(item.title) for item in items
        ):
            text = (
                f'Não encontrei a marca preferida "{preferred_product_brand}" '
                "entre os resultados; seguem as alternativas compatíveis."
            )
        text += " Preço e estoque na filial precisam ser confirmados."
        return text, ProcessAgentRequestUseCase._catalog_items_action(items)

    @staticmethod
    def _selected_candidate_action(candidate: ResultCandidateState) -> dict[str, object]:
        return {
            "type": "show_items",
            "items": [
                {
                    "item_id": candidate.item_id,
                    "title": candidate.title,
                    "score": candidate.score,
                }
            ],
        }

    async def _validate_pre_search(
        self,
        *,
        query: str,
        last_messages: list[dict[str, str]],
        incoming_state: ConversationState | None,
    ) -> tuple[PreSearchValidation, str, list[str]]:
        deterministic_validator = getattr(
            self._pre_search_validator,
            "try_validate_deterministically",
            None,
        )
        if (
            self._settings.pre_search_deterministic_bypass_enabled
            and callable(deterministic_validator)
        ):
            try:
                deterministic_result = await self._run_validator_call(
                    deterministic_validator,
                    query,
                    last_messages=last_messages,
                    conversation_state=incoming_state,
                )
            except Exception:
                self._logger.warning(
                    "pre_search_deterministic_bypass_failed",
                    exc_info=True,
                )
            else:
                if isinstance(deterministic_result, PreSearchValidation):
                    self._logger.info(
                        "pre_search_deterministic_bypass_used",
                        extra={
                            "criteria": deterministic_result.criteria.model_dump(
                                exclude_none=True
                            ),
                        },
                    )
                    return (
                        deterministic_result,
                        "deterministic_bypass",
                        ["pre_search_deterministic"],
                    )

        deterministic_ask_validator = getattr(
            self._pre_search_validator,
            "try_validate_deterministic_ask",
            None,
        )
        if (
            self._settings.pre_search_deterministic_ask_enabled
            and callable(deterministic_ask_validator)
        ):
            try:
                deterministic_ask_result = await self._run_validator_call(
                    deterministic_ask_validator,
                    query,
                    last_messages=last_messages,
                    conversation_state=incoming_state,
                )
            except Exception:
                self._logger.warning(
                    "pre_search_deterministic_ask_failed",
                    exc_info=True,
                )
            else:
                if (
                    isinstance(deterministic_ask_result, PreSearchValidation)
                    and deterministic_ask_result.decision == "ask"
                    and bool(deterministic_ask_result.missing_fields)
                    and deterministic_ask_result.next_question is not None
                    and deterministic_ask_result.next_question.key
                    == deterministic_ask_result.missing_fields[0]
                ):
                    self._logger.info(
                        "pre_search_deterministic_ask_used",
                        extra={
                            "criteria": deterministic_ask_result.criteria.model_dump(
                                exclude_none=True
                            ),
                            "missing_fields": deterministic_ask_result.missing_fields,
                            "next_question_key": (
                                deterministic_ask_result.next_question.key
                            ),
                        },
                    )
                    return (
                        deterministic_ask_result,
                        "deterministic_ask",
                        ["pre_search_deterministic_ask"],
                    )

        return (
            await self._run_validator_call(
                self._pre_search_validator.validate,
                query,
                last_messages=last_messages,
                conversation_state=incoming_state,
            ),
            "llm",
            ["pre_search_validator"],
        )

    @staticmethod
    def _build_search_query(criteria: SearchCriteria) -> str:
        tokens = [
            criteria.part_code,
            criteria.part_query,
            criteria.preferred_product_brand,
            criteria.vehicle_brand,
            criteria.vehicle_model,
            str(criteria.vehicle_year) if criteria.vehicle_year else None,
            criteria.engine,
            "esquerdo" if criteria.side == "left" else "direito" if criteria.side == "right" else None,
            "dianteiro" if criteria.position == "front" else "traseiro" if criteria.position == "rear" else None,
            "eixo dianteiro" if criteria.axle == "front" else "eixo traseiro" if criteria.axle == "rear" else None,
            criteria.variant,
        ]
        return " ".join(token for token in tokens if token)

    def _canonicalize_validated_part_query(
        self,
        pre_search: PreSearchValidation,
    ) -> PreSearchValidation:
        part_query = pre_search.criteria.part_query
        if not part_query:
            return pre_search

        canonicalizer = getattr(
            self._pre_search_validator,
            "canonicalize_part_query",
            None,
        )
        if not callable(canonicalizer):
            return pre_search

        canonical_part_query = canonicalizer(part_query)
        if canonical_part_query == part_query:
            return pre_search

        criteria_values = pre_search.criteria.model_dump(exclude_none=False)
        criteria_values["part_query"] = canonical_part_query
        criteria = SearchCriteria.model_validate(criteria_values)

        decision = pre_search.decision
        missing_fields = [
            field for field in pre_search.missing_fields if field != "part_query"
        ]
        next_question = pre_search.next_question

        if canonical_part_query is None and not criteria.part_code:
            decision = "handoff"
            missing_fields = []
            next_question = NextQuestion(
                key="handoff",
                prompt=UNSUPPORTED_PART_HANDOFF_PROMPT,
            )

        return PreSearchValidation(
            decision=decision,
            criteria=criteria,
            items=pre_search.items,
            missing_fields=missing_fields,
            next_question=next_question,
            confidence=pre_search.confidence,
        )

    @staticmethod
    def _preserve_search_continuation_criteria(
        pre_search: PreSearchValidation,
        *,
        incoming_state: ConversationState | None,
    ) -> PreSearchValidation:
        if (
            pre_search.decision != "search"
            or incoming_state is None
            or not incoming_state.pending_slot
        ):
            return pre_search

        current_part = str(pre_search.criteria.part_query or "").strip().casefold()
        state_part = str(incoming_state.criteria.part_query or "").strip().casefold()
        if current_part and state_part and current_part != state_part:
            return pre_search

        merged_values = pre_search.criteria.model_dump(exclude_none=False)
        state_values = incoming_state.criteria.model_dump(exclude_none=False)
        changed = False
        for field_name, state_value in state_values.items():
            if field_name == "part_code" or state_value in (None, "", []):
                continue
            if merged_values.get(field_name) in (None, "", []):
                merged_values[field_name] = state_value
                changed = True

        if not changed:
            return pre_search

        return PreSearchValidation(
            decision=pre_search.decision,
            criteria=SearchCriteria.model_validate(merged_values),
            items=pre_search.items,
            missing_fields=list(pre_search.missing_fields),
            next_question=pre_search.next_question,
            confidence=pre_search.confidence,
        )

    @classmethod
    def _build_no_match_reply(
        cls,
        *,
        criteria: SearchCriteria,
        missing_fields: list[str],
        incoming_state: ConversationState | None,
    ) -> tuple[str, str, str]:
        criteria_text = cls._format_searched_criteria(criteria)
        unresolved_fields = [
            field_name
            for field_name in missing_fields
            if field_name in SearchCriteria.model_fields
            and getattr(criteria, field_name, None) in (None, "", [])
        ]
        conflicts = cls._find_context_conflicts(
            criteria=criteria,
            incoming_state=incoming_state,
        )

        if unresolved_fields:
            missing_text = ", ".join(
                cls._criteria_field_label(field_name)
                for field_name in unresolved_fields
            )
            pending_question = f"Informe {missing_text} para refazer a pesquisa."
            reply_text = (
                "A consulta nao encontrou itens, mas os criterios ainda estao "
                f"insuficientes. Criterios pesquisados: {criteria_text}. "
                f"Ainda falta: {missing_text}. {pending_question} "
                "Se preferir, peca atendimento humano."
            )
            return reply_text, unresolved_fields[0], pending_question

        if conflicts:
            conflict_text = "; ".join(conflicts)
            pending_question = "Confirme ou corrija o criterio divergente para tentar novamente."
            reply_text = (
                "Nao encontrei itens no ERP para os criterios pesquisados: "
                f"{criteria_text}. Ha divergencia com o contexto anterior: "
                f"{conflict_text}. Isso nao comprova incompatibilidade da peca "
                f"com o veiculo. {pending_question} Se preferir, peca atendimento humano."
            )
            return reply_text, "no_match_retry", pending_question

        pending_question = "Corrija algum criterio para tentar novamente ou peca atendimento humano."
        reply_text = (
            "Nao encontrei itens no ERP para os criterios pesquisados: "
            f"{criteria_text}. Esse resultado informa apenas que nenhum item "
            "correspondeu a esses filtros; ele nao comprova incompatibilidade "
            f"da peca com o veiculo. {pending_question}"
        )
        return reply_text, "no_match_retry", pending_question

    @classmethod
    def _format_searched_criteria(cls, criteria: SearchCriteria) -> str:
        formatted: list[str] = []
        for field_name in (
            "part_code",
            "part_query",
            "preferred_product_brand",
            "vehicle_brand",
            "vehicle_model",
            "vehicle_year",
            "engine",
            "side",
            "position",
            "axle",
            "variant",
        ):
            value = getattr(criteria, field_name, None)
            if value in (None, "", []):
                continue
            label = cls._criteria_field_label(field_name)
            formatted.append(f'{label} "{cls._criteria_value_text(field_name, value)}"')
        return "; ".join(formatted) or "nenhum criterio utilizavel"

    @classmethod
    def _find_context_conflicts(
        cls,
        *,
        criteria: SearchCriteria,
        incoming_state: ConversationState | None,
    ) -> list[str]:
        if incoming_state is None:
            return []

        conflicts: list[str] = []
        for field_name in (
            "preferred_product_brand",
            "vehicle_brand",
            "vehicle_model",
            "vehicle_year",
            "engine",
            "side",
            "position",
            "axle",
            "variant",
        ):
            previous_value = getattr(incoming_state.criteria, field_name, None)
            current_value = getattr(criteria, field_name, None)
            if previous_value in (None, "", []) or current_value in (None, "", []):
                continue
            if str(previous_value).strip().casefold() == str(current_value).strip().casefold():
                continue
            label = cls._criteria_field_label(field_name)
            previous_text = cls._criteria_value_text(field_name, previous_value)
            current_text = cls._criteria_value_text(field_name, current_value)
            conflicts.append(
                f'{label} era "{previous_text}" e foi pesquisado como "{current_text}"'
            )
        return conflicts

    @staticmethod
    def _criteria_field_label(field_name: str) -> str:
        return {
            "part_query": "peca",
            "part_code": "codigo",
            "preferred_product_brand": "marca preferida da peca",
            "vehicle_brand": "marca",
            "vehicle_model": "modelo",
            "vehicle_year": "ano",
            "engine": "motor",
            "side": "lado",
            "position": "posicao",
            "axle": "eixo",
            "variant": "versao",
        }.get(field_name, field_name)

    @staticmethod
    def _criteria_value_text(field_name: str, value: object) -> str:
        directional_values = {
            "side": {"left": "esquerdo", "right": "direito"},
            "position": {"front": "dianteiro", "rear": "traseiro"},
            "axle": {"front": "eixo dianteiro", "rear": "eixo traseiro"},
        }
        return directional_values.get(field_name, {}).get(str(value), str(value))

    def _enforce_part_code_provenance(
        self,
        pre_search: PreSearchValidation,
        *,
        message_text: str,
        last_messages: list[dict[str, str]],
    ) -> PreSearchValidation:
        validated_items = [
            self._enforce_part_code_provenance_for_criteria(
                item,
                message_text=message_text,
                last_messages=last_messages,
            )
            for item in (pre_search.items or [])
        ] or None
        part_code = normalize_part_code_candidate(pre_search.criteria.part_code)
        if not part_code:
            if validated_items == pre_search.items:
                return pre_search
            return PreSearchValidation(
                decision=pre_search.decision,
                criteria=pre_search.criteria,
                items=validated_items,
                missing_fields=list(pre_search.missing_fields),
                next_question=pre_search.next_question,
                confidence=pre_search.confidence,
            )

        literal_evidence = has_literal_part_code_evidence(
            part_code,
            message_text=message_text,
            last_messages=last_messages,
        )
        extractor_evidence = self._part_code_validated_by_extractor(
            part_code=part_code,
            message_text=message_text,
            last_messages=last_messages,
        )
        if literal_evidence or extractor_evidence:
            if (
                part_code == pre_search.criteria.part_code
                and validated_items == pre_search.items
            ):
                return pre_search
            criteria_values = pre_search.criteria.model_dump(exclude_none=False)
            criteria_values["part_code"] = part_code
            return PreSearchValidation(
                decision=pre_search.decision,
                criteria=SearchCriteria.model_validate(criteria_values),
                items=validated_items,
                missing_fields=list(pre_search.missing_fields),
                next_question=pre_search.next_question,
                confidence=pre_search.confidence,
            )

        self._logger.warning(
            "part_code_rejected_without_provenance",
            extra={"part_code": part_code},
        )
        criteria_values = pre_search.criteria.model_dump(exclude_none=False)
        criteria_values["part_code"] = None
        criteria = SearchCriteria.model_validate(criteria_values)
        decision = pre_search.decision
        missing_fields = [
            field for field in pre_search.missing_fields if field != "part_code"
        ]
        next_question = pre_search.next_question
        if next_question is not None and next_question.key == "part_code":
            next_question = None

        if decision == "search" and not criteria.part_query:
            decision = "ask"
            if "part_query" not in missing_fields:
                missing_fields.insert(0, "part_query")
            next_question = NextQuestion(
                key="part_query",
                prompt="Qual peca voce precisa?",
            )

        return PreSearchValidation(
            decision=decision,
            criteria=criteria,
            items=validated_items,
            missing_fields=missing_fields,
            next_question=next_question,
            confidence=pre_search.confidence,
        )

    def _enforce_part_code_provenance_for_criteria(
        self,
        criteria: SearchCriteria,
        *,
        message_text: str,
        last_messages: list[dict[str, str]],
    ) -> SearchCriteria:
        part_code = normalize_part_code_candidate(criteria.part_code)
        if not part_code:
            return criteria
        if has_literal_part_code_evidence(
            part_code,
            message_text=message_text,
            last_messages=last_messages,
        ) or self._part_code_validated_by_extractor(
            part_code=part_code,
            message_text=message_text,
            last_messages=last_messages,
        ):
            if part_code == criteria.part_code:
                return criteria
            values = criteria.model_dump(exclude_none=False)
            values["part_code"] = part_code
            return SearchCriteria.model_validate(values)

        self._logger.warning(
            "part_code_rejected_without_provenance",
            extra={"part_code": part_code},
        )
        values = criteria.model_dump(exclude_none=False)
        values["part_code"] = None
        return SearchCriteria.model_validate(values)

    def _part_code_validated_by_extractor(
        self,
        *,
        part_code: str,
        message_text: str,
        last_messages: list[dict[str, str]],
    ) -> bool:
        extractor = getattr(
            self._pre_search_validator,
            "extract_dictionary_seed_criteria",
            None,
        )
        if not callable(extractor):
            return False
        try:
            criteria = extractor(
                message_text=message_text,
                last_messages=last_messages,
            )
        except Exception:
            return False
        extracted_part_code = normalize_part_code_candidate(
            getattr(criteria, "part_code", None)
        )
        return extracted_part_code == part_code

    async def _record_review_case(
        self,
        *,
        payload: AgentRequestV1,
        last_messages: list[dict[str, str]],
        pre_search: PreSearchValidation,
        result: ProcessResult,
        search_query: str | None,
        include_validator_audit: bool = True,
    ) -> None:
        try:
            audit_info = self._validator_audit_info() if include_validator_audit else {}
            review_actions = list(result.actions)
            if result.item_results:
                review_actions.append(
                    {
                        "type": "item_search_results",
                        "items": [
                            item.model_dump(exclude_none=True)
                            for item in result.item_results
                        ],
                    }
                )
            await asyncio.to_thread(
                self._review_recorder.record_interaction,
                trace_id=payload.trace_id,
                conversation_id=payload.conversation_id,
                branch_id=payload.business.branch_id,
                channel_name=payload.channel.name if payload.channel else None,
                schema_version=payload.schema_version,
                message_text=payload.message.text,
                last_messages=last_messages,
                predicted_decision=pre_search.decision,
                predicted_criteria=pre_search.criteria.model_dump(exclude_none=True),
                predicted_items=[
                    item.model_dump(exclude_none=True)
                    for item in (result.conversation_state.items or [])
                ],
                predicted_missing_fields=list(pre_search.missing_fields),
                predicted_next_question=(
                    pre_search.next_question.model_dump(exclude_none=True)
                    if pre_search.next_question is not None
                    else None
                ),
                predicted_confidence=pre_search.confidence,
                final_reply_text=result.reply_text,
                final_actions=review_actions,
                final_handoff_required=result.handoff.required,
                final_handoff_reason=result.handoff.reason,
                final_confidence=result.confidence,
                final_used_tools=list(result.tool_trace.used_tools),
                final_latency_ms=result.tool_trace.latency_ms,
                search_query=search_query,
                llm_model=self._settings.llm_model,
                llm_num_predict=self._settings.llm_num_predict,
                llm_endpoint_used=audit_info.get("llm_endpoint_used"),
                llm_raw_content=audit_info.get("llm_raw_content"),
                llm_output_valid=audit_info.get("llm_output_valid"),
                llm_parse_error=audit_info.get("llm_parse_error"),
                llm_fallback_used=audit_info.get("llm_fallback_used"),
                llm_decision_raw=audit_info.get("llm_decision_raw"),
            )
        except Exception:
            self._logger.warning(
                "pre_search_review_capture_failed",
                extra={
                    "trace_id": payload.trace_id,
                    "conversation_id": payload.conversation_id,
                },
            )

    def _validator_audit_info(self) -> dict[str, Any]:
        return dict(self._request_audit_info.get())

    def _validator_audit_info_from_validator(self) -> dict[str, Any]:
        getter = getattr(self._pre_search_validator, "get_last_audit", None)
        if not callable(getter):
            return {}
        try:
            result = getter()
        except Exception:
            return {}
        if not isinstance(result, dict):
            return {}
        return result

    @staticmethod
    def _build_conversation_state(
        *,
        criteria: SearchCriteria,
        last_decision: str,
        next_question: NextQuestion | None = None,
        pending_slot: str | None = None,
        pending_question: str | None = None,
        items: list[SearchCriteria] | None = None,
        active_item_index: int | None = None,
        item_results: list[ItemSearchResult] | None = None,
    ) -> ConversationState:
        resolved_pending_slot = pending_slot
        resolved_pending_question = pending_question

        if next_question is not None:
            resolved_pending_slot = next_question.key
            resolved_pending_question = next_question.prompt

        return ConversationState(
            criteria=criteria,
            items=items,
            active_item_index=active_item_index,
            item_results=item_results,
            pending_slot=resolved_pending_slot,
            pending_question=resolved_pending_question,
            last_decision=last_decision,
        )

    def _extract_state_items(
        self,
        *,
        query: str,
        criteria: SearchCriteria,
        incoming_state: ConversationState | None,
    ) -> list[SearchCriteria]:
        extractor = getattr(self._pre_search_validator, "extract_items", None)
        if callable(extractor):
            try:
                extracted = [item for item in extractor(query) if isinstance(item, SearchCriteria)]
            except Exception:
                extracted = []
            if len(extracted) > 1:
                return extracted
        if (
            incoming_state
            and incoming_state.items
            and (
                not criteria.part_query
                or incoming_state.active_item_index is not None
            )
        ):
            return list(incoming_state.items)
        return None

    @staticmethod
    def _apply_active_item_follow_up(
        *,
        items: list[SearchCriteria] | None,
        criteria: SearchCriteria,
        incoming_state: ConversationState | None,
    ) -> list[SearchCriteria] | None:
        """Replace only the pending item after a short follow-up answer."""
        if not items or not incoming_state or incoming_state.active_item_index is None:
            return items
        index = incoming_state.active_item_index
        if index < 0 or index >= len(items):
            return items
        pending_value = (
            getattr(criteria, incoming_state.pending_slot, None)
            if incoming_state.pending_slot
            else None
        )
        active_part = str(incoming_state.criteria.part_query or "").casefold()
        updated_part = str(criteria.part_query or "").casefold()
        is_same_active_part = bool(active_part and active_part == updated_part)
        is_explicit_active_correction = (
            is_same_active_part and criteria != incoming_state.criteria
        )
        if pending_value in (None, "", []) and not is_explicit_active_correction:
            return items
        updated = list(items)
        updated[index] = criteria
        return updated

    @staticmethod
    def _first_incomplete_item_index(
        item_gates: list[PreSearchValidation],
    ) -> int | None:
        for index, item_gate in enumerate(item_gates):
            if item_gate.decision != "search":
                return index
        return None

    @staticmethod
    def _retained_item_result(
        *,
        item_index: int,
        incoming_state: ConversationState | None,
    ) -> ItemSearchResult | None:
        """Reuse a completed sibling while the active item is being resolved."""
        if not incoming_state or incoming_state.active_item_index is None:
            return None
        if item_index == incoming_state.active_item_index:
            return None
        previous = incoming_state.item_results or []
        if item_index >= len(previous):
            return None
        result = previous[item_index]
        if result.status not in {"found", "not_found"}:
            return None
        return result

    async def _validate_items_for_search(
        self,
        *,
        items: list[SearchCriteria] | None,
        message_text: str,
        last_messages: list[dict[str, str]],
    ) -> list[PreSearchValidation]:
        """Fail closed unless every multi-item row passed its own backend gate."""
        if not items or len(items) < 2:
            return []

        validator = getattr(self._pre_search_validator, "validate_item_for_search", None)
        if not callable(validator):
            self._logger.warning("multi_item_gate_unavailable")
            return [
                PreSearchValidation(
                    decision="ask",
                    criteria=item,
                    missing_fields=["part_query"],
                    next_question=NextQuestion(
                        key="part_query",
                        prompt="Qual peca voce precisa?",
                    ),
                    confidence=0.0,
                )
                for item in items
            ]

        gated_items: list[PreSearchValidation] = []
        for item in items:
            try:
                item_validation = await self._run_validator_call(
                    validator,
                    item,
                    message_text=message_text,
                    last_messages=last_messages,
                )
            except Exception:
                self._logger.warning("multi_item_gate_failed", exc_info=True)
                item_validation = None
            if not isinstance(item_validation, PreSearchValidation):
                gated_items.append(
                    PreSearchValidation(
                        decision="ask",
                        criteria=item,
                        missing_fields=["part_query"],
                        next_question=NextQuestion(
                            key="part_query",
                            prompt="Qual peca voce precisa?",
                        ),
                        confidence=0.0,
                    )
                )
                continue
            gated_items.append(item_validation)
        return gated_items

    async def _run_validator_call(self, function: Any, /, *args: Any, **kwargs: Any) -> Any:
        """Run synchronous validator work outside the API event loop.

        The validator instance is shared by requests.  Its audit record is
        captured in the same worker that produced the validation and stored in
        this request's ContextVar, preventing another request from overwriting
        review telemetry before it is recorded.
        """
        timeout_s = max(self._settings.llm_timeout_ms / 1000, 0.1)
        try:
            async with self._llm_semaphore:
                result, audit_info = await asyncio.wait_for(
                    asyncio.to_thread(self._call_validator_and_capture_audit, function, args, kwargs),
                    timeout=timeout_s,
                )
        except TimeoutError as exc:
            raise PreSearchServiceUnavailableError(
                "Validador de pesquisa indisponivel: tempo limite excedido."
            ) from exc
        self._request_audit_info.set(audit_info)
        return result

    def _call_validator_and_capture_audit(
        self,
        function: Any,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> tuple[Any, dict[str, Any]]:
        result = function(*args, **kwargs)
        return result, self._validator_audit_info_from_validator()

    async def _search_parts(
        self,
        *,
        query: str,
        branch_id: int,
        criteria: SearchCriteria,
    ) -> list[Any]:
        timeout_s = max(self._settings.erp_search_timeout_ms / 1000, 0.1)
        try:
            async with self._erp_search_semaphore:
                return await asyncio.wait_for(
                    asyncio.to_thread(
                        self._tools.search_parts,
                        query=query,
                        branch_id=branch_id,
                        criteria=criteria,
                    ),
                    timeout=timeout_s,
                )
        except TimeoutError as exc:
            raise SearchPartsServiceUnavailableError(
                "Busca de pecas indisponivel: tempo limite excedido."
            ) from exc
