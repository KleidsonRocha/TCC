import logging
import time
from contextlib import contextmanager
from typing import Any, Iterator

from app.api.schemas.contract_v1 import AgentRequestV1
from app.config import Settings
from app.core.domain.part_code import (
    has_literal_part_code_evidence,
    normalize_part_code_candidate,
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
    RESULT_DISAMBIGUATION_SLOT,
    build_result_disambiguation_state,
    resolve_result_disambiguation,
)
from app.core.domain.rules import validate_message_text, validate_schema_version
from app.core.ports.pre_search_review_recorder import PreSearchReviewRecorderPort
from app.core.ports.pre_search_validator import PreSearchValidatorPort
from app.core.ports.tools import ToolsPort

UNSUPPORTED_PART_HANDOFF_PROMPT = (
    "Essa familia de peca nao esta no catalogo para pesquisa automatica. "
    "Vou encaminhar para atendimento humano."
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

    async def execute(self, payload: AgentRequestV1) -> ProcessResult:
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
        disambiguation_result, restart_conversation = self._try_result_disambiguation(
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

        with timing.measure("pre_search_validator"):
            pre_search, pre_search_path, used_tools = self._validate_pre_search(
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
            state_items = self._extract_state_items(
                query=query,
                criteria=pre_search.criteria,
                incoming_state=incoming_state,
            )
            if pre_search.items and len(pre_search.items) > 1:
                state_items = list(pre_search.items)
            current_state = self._build_conversation_state(
                criteria=pre_search.criteria,
                last_decision=pre_search.decision,
                next_question=pre_search.next_question,
                items=state_items,
            )
            actions: list[dict[str, object]] = []
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
            self._record_review_case(
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
            self._record_review_case(
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
            self._record_review_case(
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
            for item_criteria_row in item_criteria:
                item_query = self._build_search_query(item_criteria_row)
                if not item_query.strip():
                    item_results.append(ItemSearchResult(item=item_criteria_row, status="incomplete"))
                    continue
                used_tools.append("search_parts")
                try:
                    found_items = self._tools.search_parts(
                        query=item_query,
                        branch_id=payload.business.branch_id,
                        criteria=item_criteria_row,
                    )
                    item_results.append(ItemSearchResult(
                        item=item_criteria_row,
                        status="found" if found_items else "not_found",
                        products=found_items,
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
                    "Para garantir o encaixe, confirme motorizacao, lado e versao do veiculo."
                )
                confidence = 0.93
            else:
                disambiguation = build_result_disambiguation_state(items)
                reply_text = disambiguation.prompt
                actions = [self._result_disambiguation_action(disambiguation)]
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
        self._record_review_case(
            payload=payload,
            last_messages=last_messages,
            pre_search=pre_search,
            result=result,
            search_query=search_query,
        )
        return result

    def _try_result_disambiguation(
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
            elif resolution.kind in {"ask", "unresolved"} and resolution.state is not None:
                disambiguation = resolution.state
                reply_text = disambiguation.prompt
                if resolution.kind == "unresolved":
                    reply_text = f"Nao consegui identificar a opcao. {reply_text}"
                action = self._result_disambiguation_action(disambiguation)
                actions = [action]
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
        self._record_review_case(
            payload=payload,
            last_messages=[],
            pre_search=synthetic_validation,
            result=result,
            search_query=None,
            include_validator_audit=False,
        )
        return result, False

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

    @staticmethod
    def _result_disambiguation_action(
        state: ResultDisambiguationState,
    ) -> dict[str, object]:
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

    def _validate_pre_search(
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
                deterministic_result = deterministic_validator(
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
                deterministic_ask_result = deterministic_ask_validator(
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
            self._pre_search_validator.validate(
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
            "position": {"front": "dianteira", "rear": "traseira"},
            "axle": {"front": "dianteiro", "rear": "traseiro"},
        }
        return directional_values.get(field_name, {}).get(str(value), str(value))

    def _enforce_part_code_provenance(
        self,
        pre_search: PreSearchValidation,
        *,
        message_text: str,
        last_messages: list[dict[str, str]],
    ) -> PreSearchValidation:
        part_code = normalize_part_code_candidate(pre_search.criteria.part_code)
        if not part_code:
            return pre_search

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
            if part_code == pre_search.criteria.part_code:
                return pre_search
            criteria_values = pre_search.criteria.model_dump(exclude_none=False)
            criteria_values["part_code"] = part_code
            return PreSearchValidation(
                decision=pre_search.decision,
                criteria=SearchCriteria.model_validate(criteria_values),
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
            missing_fields=missing_fields,
            next_question=next_question,
            confidence=pre_search.confidence,
        )

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

    def _record_review_case(
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
            self._review_recorder.record_interaction(
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
                final_actions=list(result.actions),
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
    ) -> ConversationState:
        resolved_pending_slot = pending_slot
        resolved_pending_question = pending_question

        if next_question is not None:
            resolved_pending_slot = next_question.key
            resolved_pending_question = next_question.prompt

        return ConversationState(
            criteria=criteria,
            items=items,
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
        if incoming_state and incoming_state.items and not criteria.part_query:
            return list(incoming_state.items)
        return None
