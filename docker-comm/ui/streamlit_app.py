from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any
from urllib.parse import quote
from uuid import uuid4

import httpx
import streamlit as st


DEFAULT_COMM_API_URL = "http://docker-comm:8000"
DEFAULT_SOURCE = "webchat"
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_REVIEW_API_URL = "http://docker-agent:8001"
REVIEW_CRITERIA_FIELDS = (
    "part_query",
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
    "quantity",
)
REVIEW_FIELD_LABELS = {
    "part_query": "Peça/família",
    "part_code": "Código da peça",
    "preferred_product_brand": "Marca preferida da peça",
    "vehicle_brand": "Marca do veículo",
    "vehicle_model": "Modelo do veículo",
    "vehicle_year": "Ano",
    "engine": "Motor",
    "side": "Lado",
    "position": "Posição",
    "axle": "Eixo",
    "variant": "Versão/variante",
    "quantity": "Quantidade",
}
REVIEW_DIRECTION_OPTIONS = {
    "side": {"": "Não informado", "left": "Esquerdo", "right": "Direito"},
    "position": {"": "Não informado", "front": "Dianteira", "rear": "Traseira"},
    "axle": {"": "Não informado", "front": "Dianteiro", "rear": "Traseiro"},
}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _init_state() -> None:
    st.session_state.setdefault("conversation_id", str(uuid4()))
    st.session_state.setdefault("conversation_id_input", st.session_state.conversation_id)
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("request_log", [])
    st.session_state.setdefault("last_response", None)
    st.session_state.setdefault("comm_api_url", os.getenv("COMM_API_URL", DEFAULT_COMM_API_URL))
    st.session_state.setdefault("source", os.getenv("STREAMLIT_SOURCE", DEFAULT_SOURCE))
    st.session_state.setdefault("branch_id", _env_int("DEFAULT_BRANCH_ID", 1))
    st.session_state.setdefault("review_api_url", os.getenv("REVIEW_API_URL", DEFAULT_REVIEW_API_URL))
    st.session_state.setdefault("reviewed_by", os.getenv("REVIEWED_BY", ""))
    st.session_state.setdefault("review_flash", None)


def _headers() -> dict[str, str]:
    api_key = os.getenv("COMM_API_KEY") or os.getenv("API_KEY")
    if not api_key:
        return {}
    return {"X-API-Key": api_key}


def _review_headers() -> dict[str, str]:
    api_key = os.getenv("REVIEW_API_KEY")
    if not api_key:
        return {}
    return {"X-Review-Key": api_key}


def _review_request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base_url = str(st.session_state.review_api_url).rstrip("/")
    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.request(
                method,
                f"{base_url}{path}",
                params=params,
                json=payload,
                headers=_review_headers(),
            )
    except httpx.HTTPError as exc:
        return {"ok": False, "status_code": None, "error": str(exc)}
    try:
        body = response.json()
    except ValueError:
        body = {"detail": response.text}
    if response.is_error:
        detail = body.get("detail") if isinstance(body, dict) else response.text
        return {"ok": False, "status_code": response.status_code, "error": str(detail), "body": body}
    return {"ok": True, "status_code": response.status_code, "body": body}


def _optional_positive_int(raw: Any, *, field_label: str) -> int | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        value = int(text)
    except ValueError as exc:
        raise ValueError(f"{field_label} deve ser um número inteiro.") from exc
    if value <= 0:
        raise ValueError(f"{field_label} deve ser maior que zero.")
    return value


def _build_review_criteria(values: dict[str, Any]) -> dict[str, Any]:
    criteria: dict[str, Any] = {}
    for key in REVIEW_CRITERIA_FIELDS:
        value = values.get(key)
        if key in {"vehicle_year", "quantity"}:
            parsed = _optional_positive_int(value, field_label=REVIEW_FIELD_LABELS[key])
            if parsed is not None:
                if key == "vehicle_year" and not 1900 <= parsed <= 2100:
                    raise ValueError("Ano deve estar entre 1900 e 2100.")
                if key == "quantity" and parsed > 999:
                    raise ValueError("Quantidade deve estar entre 1 e 999.")
                criteria[key] = parsed
            continue
        text = str(value or "").strip()
        if text:
            criteria[key] = text
    return criteria


def _build_review_items(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for index, raw in enumerate(values, start=1):
        criteria = _build_review_criteria(raw.get("criteria") or {})
        if not criteria.get("part_query") and not criteria.get("part_code"):
            raise ValueError(f"Peça {index}: informe a família ou o código.")
        decision = str(raw.get("decision") or "search")
        question_key = str(raw.get("question_key") or "").strip() or None
        question_prompt = str(raw.get("question_prompt") or "").strip() or None
        if decision == "ask" and (not question_key or not question_prompt):
            raise ValueError(f"Peça {index}: informe o campo e o texto da pergunta.")
        if decision == "ask" and not raw.get("missing_fields"):
            raise ValueError(f"Peça {index}: informe ao menos um campo faltante.")
        if decision == "search" and raw.get("missing_fields"):
            raise ValueError(f"Peça {index}: uma peça pronta para busca não pode ter campos faltantes.")
        items.append({
            "decision": decision,
            "criteria": criteria,
            "missing_fields": list(raw.get("missing_fields") or []),
            "question_key": question_key,
            "question_prompt": question_prompt,
            "question_options": list(raw.get("question_options") or []) or None,
        })
    return items


def _send_message(*, text: str) -> dict[str, Any]:
    base_url = str(st.session_state.comm_api_url).rstrip("/")
    payload = {
        "source": st.session_state.source,
        "conversation_id": st.session_state.conversation_id,
        "text": text,
        "branch_id": int(st.session_state.branch_id),
    }

    started_at = time.perf_counter()
    try:
        with httpx.Client(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
            response = client.post(
                f"{base_url}/test/send",
                json=payload,
                headers=_headers(),
            )
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
    except httpx.HTTPError as exc:
        return {
            "ok": False,
            "latency_ms": round((time.perf_counter() - started_at) * 1000, 2),
            "status_code": None,
            "error": str(exc),
        }

    try:
        body = response.json()
    except ValueError:
        body = {"detail": response.text}

    if response.is_error:
        detail = body.get("detail") if isinstance(body, dict) else response.text
        return {
            "ok": False,
            "latency_ms": latency_ms,
            "status_code": response.status_code,
            "error": str(detail),
            "body": body,
        }

    return {
        "ok": True,
        "latency_ms": latency_ms,
        "status_code": response.status_code,
        "body": body,
    }


def _check_comm_health() -> dict[str, Any]:
    base_url = str(st.session_state.comm_api_url).rstrip("/")
    started_at = time.perf_counter()
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{base_url}/health")
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
    except httpx.HTTPError as exc:
        return {"ok": False, "latency_ms": None, "detail": str(exc)}

    return {
        "ok": response.is_success,
        "latency_ms": latency_ms,
        "status_code": response.status_code,
        "detail": response.text,
    }


def _record_usage(*, text: str, result: dict[str, Any]) -> None:
    body = result.get("body") if isinstance(result.get("body"), dict) else {}
    handoff = body.get("handoff") if isinstance(body, dict) else {}
    actions = body.get("actions") if isinstance(body, dict) else []

    st.session_state.request_log.append(
        {
            "time": datetime.now().strftime("%H:%M:%S"),
            "status": "ok" if result.get("ok") else "erro",
            "http_status": result.get("status_code"),
            "latency_ms": result.get("latency_ms"),
            "confidence": body.get("confidence"),
            "trace_id": body.get("trace_id"),
            "actions": len(actions) if isinstance(actions, list) else 0,
            "handoff": bool(handoff.get("required")) if isinstance(handoff, dict) else False,
            "message": text,
        }
    )
    st.session_state.last_response = result


def _reset_conversation() -> None:
    conversation_id = str(uuid4())
    st.session_state.conversation_id = conversation_id
    st.session_state.conversation_id_input = conversation_id
    st.session_state.messages = []
    st.session_state.request_log = []
    st.session_state.last_response = None


def _render_sidebar() -> None:
    with st.sidebar:
        if st.button("Nova conversa", use_container_width=True):
            _reset_conversation()

        st.text_input("Comm API", key="comm_api_url")
        st.text_input("Origem", key="source")
        st.number_input("Filial", min_value=1, step=1, key="branch_id")

        conversation_id = st.text_input("Conversa", key="conversation_id_input")
        if conversation_id.strip():
            st.session_state.conversation_id = conversation_id.strip()

        health = _check_comm_health()
        status = "online" if health["ok"] else "offline"
        st.metric("Gateway", status, f"{health.get('latency_ms') or 0:.0f} ms")


def _render_actions(actions: list[dict[str, Any]] | None) -> None:
    if not actions:
        return

    for action in actions:
        action_type = action.get("type")
        if action_type == "show_items":
            items = action.get("items")
            if not isinstance(items, list) or not items:
                continue

            rows = [
                {
                    "Codigo": item.get("item_id"),
                    "Descricao": item.get("title"),
                    "Score": item.get("score"),
                }
                for item in items
                if isinstance(item, dict)
            ]
            if not rows:
                continue

            st.dataframe(
                rows,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Codigo": st.column_config.TextColumn("Codigo", width="small"),
                    "Descricao": st.column_config.TextColumn("Descricao", width="large"),
                    "Score": st.column_config.NumberColumn("Score", format="%.2f"),
                },
            )
        elif action_type == "request_info":
            options = action.get("options")
            if isinstance(options, list) and options:
                st.caption("Opcoes sugeridas: " + " | ".join(str(option) for option in options))
        else:
            with st.expander(f"Acao: {action_type or 'desconhecida'}"):
                st.json(action)


def _render_chat() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["text"])
            if message["role"] == "assistant":
                _render_actions(message.get("actions"))

    prompt = st.chat_input("Digite a mensagem do cliente")
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "text": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consultando atendimento..."):
            result = _send_message(text=prompt)

        _record_usage(text=prompt, result=result)
        if result["ok"]:
            body = result["body"]
            st.session_state.conversation_id = body.get("conversation_id") or st.session_state.conversation_id
            reply = str(body.get("reply") or "")
            actions = body.get("actions") if isinstance(body.get("actions"), list) else []
            st.write(reply)
            _render_actions(actions)
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "text": reply,
                    "actions": actions,
                }
            )
        else:
            error = result.get("error") or "Falha ao consultar o docker-comm."
            st.error(error)
            st.session_state.messages.append({"role": "assistant", "text": error})


def _render_usage() -> None:
    records = st.session_state.request_log
    successes = [record for record in records if record["status"] == "ok"]
    failures = len(records) - len(successes)
    latencies = [
        float(record["latency_ms"])
        for record in records
        if isinstance(record.get("latency_ms"), int | float)
    ]
    average_latency = sum(latencies) / len(latencies) if latencies else 0
    last = records[-1] if records else {}

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Requisicoes", len(records))
    col2.metric("Sucesso", len(successes))
    col3.metric("Erros", failures)
    col4.metric("Latencia media", f"{average_latency:.0f} ms")

    col5, col6, col7 = st.columns(3)
    confidence = last.get("confidence")
    col5.metric("Ultima confianca", "-" if confidence is None else f"{float(confidence):.2f}")
    col6.metric("Acoes retornadas", int(last.get("actions") or 0))
    col7.metric("Handoff", "sim" if last.get("handoff") else "nao")

    if latencies:
        st.line_chart(latencies)

    st.dataframe(records, hide_index=True, use_container_width=True)

    if st.session_state.last_response is not None:
        with st.expander("Ultima resposta bruta"):
            st.json(st.session_state.last_response)


def _conversation_label(summary: dict[str, Any]) -> str:
    preview = str(summary.get("latest_message") or "").replace("\n", " ").strip()
    if len(preview) > 72:
        preview = preview[:69] + "..."
    return (
        f"{summary.get('conversation_id')} · "
        f"{summary.get('pending_count', 0)} pendente(s) · {preview}"
    )


def _render_review_timeline(interactions: list[dict[str, Any]], selected_id: int | None) -> None:
    st.subheader("Conversa completa")
    first_history = interactions[0].get("last_messages") if interactions else []
    if isinstance(first_history, list) and first_history:
        st.caption("Contexto anterior ao primeiro registro capturado")
        for message in first_history:
            if not isinstance(message, dict):
                continue
            role = "assistant" if message.get("role") == "assistant" else "user"
            with st.chat_message(role):
                st.write(message.get("text") or "")

    for interaction in interactions:
        interaction_id = int(interaction["id"])
        selected = interaction_id == selected_id
        status_label = str(interaction.get("review_status") or "pending")
        st.markdown(f"**Turno #{interaction_id} · {status_label}{' · selecionado' if selected else ''}**")
        with st.chat_message("user"):
            st.write(interaction.get("message_text") or "")
        with st.chat_message("assistant"):
            st.write(interaction.get("final_reply_text") or "")
        with st.expander(f"Dados técnicos do turno #{interaction_id}", expanded=False):
            st.write("Decisão prevista:", interaction.get("predicted_decision"))
            st.write("Critérios previstos:")
            st.json(interaction.get("predicted_criteria") or {})
            st.write("Itens previstos:")
            st.json(interaction.get("predicted_items") or [])
            st.write("Campos faltantes:", interaction.get("predicted_missing_fields") or [])
            st.write("Próxima pergunta:")
            st.json(interaction.get("predicted_next_question") or {})
            st.write("Ferramentas:", interaction.get("final_used_tools") or [])
            st.write("Latência:", interaction.get("final_latency_ms"), "ms")
            if interaction.get("review_status") != "pending":
                st.write("Revisão registrada:")
                st.json({
                    "decision": interaction.get("reviewed_decision"),
                    "criteria": interaction.get("reviewed_criteria"),
                    "items": interaction.get("reviewed_items"),
                    "missing_fields": interaction.get("reviewed_missing_fields"),
                    "question_key": interaction.get("reviewed_question_key"),
                    "question_prompt": interaction.get("reviewed_question_prompt"),
                    "notes": interaction.get("reviewed_notes"),
                    "reviewed_by": interaction.get("reviewed_by"),
                })
                if interaction.get("review_history"):
                    st.write("Histórico de alterações:")
                    st.json(interaction.get("review_history"))


def _submit_review(interaction: dict[str, Any], *, discard: bool = False) -> None:
    interaction_id = int(interaction["id"])
    reviewer = str(st.session_state.reviewed_by or "").strip()
    if not reviewer:
        st.error("Informe o nome do avaliador.")
        return

    notes = str(st.session_state.get(f"review_notes_{interaction_id}", "")).strip() or None
    if discard:
        result = _review_request(
            "POST",
            f"/review/interactions/{interaction_id}/discard",
            payload={"reviewed_by": reviewer, "reviewed_notes": notes},
        )
    else:
        decision = str(st.session_state.get(f"review_decision_{interaction_id}", ""))
        raw_values = {
            key: st.session_state.get(f"review_{key}_{interaction_id}", "")
            for key in REVIEW_CRITERIA_FIELDS
        }
        try:
            criteria = _build_review_criteria(raw_values)
            item_count = int(st.session_state.get(f"review_item_count_{interaction_id}", 0))
            raw_items: list[dict[str, Any]] = []
            for item_index in range(item_count):
                item_options_text = str(
                    st.session_state.get(
                        f"review_item_options_{interaction_id}_{item_index}", ""
                    )
                )
                raw_items.append({
                    "decision": st.session_state.get(
                        f"review_item_decision_{interaction_id}_{item_index}", "search"
                    ),
                    "criteria": {
                        key: st.session_state.get(
                            f"review_item_{key}_{interaction_id}_{item_index}", ""
                        )
                        for key in REVIEW_CRITERIA_FIELDS
                    },
                    "missing_fields": st.session_state.get(
                        f"review_item_missing_{interaction_id}_{item_index}", []
                    ),
                    "question_key": st.session_state.get(
                        f"review_item_question_key_{interaction_id}_{item_index}", ""
                    ),
                    "question_prompt": st.session_state.get(
                        f"review_item_question_prompt_{interaction_id}_{item_index}", ""
                    ),
                    "question_options": [
                        value.strip() for value in item_options_text.splitlines() if value.strip()
                    ],
                })
            review_items = _build_review_items(raw_items) if raw_items else None
        except ValueError as exc:
            st.error(str(exc))
            return
        question_key = str(st.session_state.get(f"review_question_key_{interaction_id}", "")).strip() or None
        question_prompt = str(st.session_state.get(f"review_question_prompt_{interaction_id}", "")).strip() or None
        options_text = str(st.session_state.get(f"review_question_options_{interaction_id}", ""))
        question_options = [item.strip() for item in options_text.splitlines() if item.strip()] or None
        if decision == "ask" and (not question_key or not question_prompt):
            st.error("Para 'Perguntar', informe o campo e o texto da próxima pergunta.")
            return
        result = _review_request(
            "PUT",
            f"/review/interactions/{interaction_id}",
            payload={
                "decision": decision,
                "criteria": criteria,
                "items": review_items,
                "missing_fields": st.session_state.get(f"review_missing_{interaction_id}", []),
                "question_key": question_key,
                "question_prompt": question_prompt,
                "question_options": question_options,
                "reviewed_notes": notes,
                "reviewed_by": reviewer,
            },
        )
    if not result.get("ok"):
        if result.get("status_code") == 409:
            st.warning("Este turno já foi avaliado por outra sessão.")
        else:
            st.error(result.get("error") or "Não foi possível salvar a revisão.")
        return
    body = result.get("body") or {}
    if body.get("conversation_completed"):
        message = "Conversa avaliada. Ela saiu da fila de pendentes."
    else:
        message = f"Turno #{interaction_id} avaliado. Ainda existem {body.get('pending_count', 0)} turno(s) pendente(s)."
    st.session_state.review_flash = message
    st.rerun()


def _render_review_form(interaction: dict[str, Any]) -> None:
    interaction_id = int(interaction["id"])
    predicted = interaction.get("reviewed_criteria") or interaction.get("predicted_criteria") or {}
    predicted_question = interaction.get("predicted_next_question") or {}
    predicted_decision = interaction.get("reviewed_decision") or interaction.get("predicted_decision") or "ask"
    options = predicted_question.get("options") if isinstance(predicted_question, dict) else []

    st.subheader(f"Avaliar turno #{interaction_id}")
    st.caption("Corrija os campos abaixo. Campos vazios não entram no exemplo revisado.")
    st.selectbox(
        "Decisão correta",
        options=["ask", "search", "handoff"],
        index=["ask", "search", "handoff"].index(predicted_decision) if predicted_decision in {"ask", "search", "handoff"} else 0,
        format_func=lambda value: {"ask": "Perguntar", "search": "Buscar", "handoff": "Encaminhar"}[value],
        key=f"review_decision_{interaction_id}",
    )
    columns = st.columns(2)
    for index, key in enumerate(REVIEW_CRITERIA_FIELDS):
        with columns[index % 2]:
            if key in REVIEW_DIRECTION_OPTIONS:
                direction_options = REVIEW_DIRECTION_OPTIONS[key]
                predicted_value = str(predicted.get(key) or "")
                if predicted_value not in direction_options:
                    predicted_value = ""
                st.selectbox(
                    REVIEW_FIELD_LABELS[key],
                    options=list(direction_options),
                    index=list(direction_options).index(predicted_value),
                    format_func=lambda value, choices=direction_options: choices[value],
                    key=f"review_{key}_{interaction_id}",
                )
            else:
                st.text_input(
                    REVIEW_FIELD_LABELS[key],
                    value="" if predicted.get(key) is None else str(predicted.get(key)),
                    key=f"review_{key}_{interaction_id}",
                )
    st.caption("Preencha código da peça somente quando ele tiver sido escrito pelo usuário na conversa.")

    st.markdown("### Peças do pedido")
    st.caption("Use mais de um cartão quando a mensagem pedir várias peças. Cada peça pode ter sua própria decisão e pendências.")
    raw_seeds = interaction.get("reviewed_items") or interaction.get("predicted_items") or []
    seeds = [
        item if "criteria" in item else {"criteria": item, "decision": predicted_decision}
        for item in raw_seeds
        if isinstance(item, dict)
    ]
    shared_defaults = {
        key: predicted.get(key)
        for key in (
            "preferred_product_brand",
            "vehicle_brand",
            "vehicle_model",
            "vehicle_year",
            "engine",
        )
        if predicted.get(key) is not None
    }
    count_key = f"review_item_count_{interaction_id}"
    st.session_state.setdefault(count_key, len(seeds))
    add_col, remove_col = st.columns(2)
    if add_col.button("Adicionar peça", key=f"add_review_item_{interaction_id}", use_container_width=True):
        st.session_state[count_key] = min(20, int(st.session_state[count_key]) + 1)
        st.rerun()
    if remove_col.button(
        "Remover última peça",
        key=f"remove_review_item_{interaction_id}",
        use_container_width=True,
        disabled=int(st.session_state[count_key]) == 0,
    ):
        st.session_state[count_key] = max(0, int(st.session_state[count_key]) - 1)
        st.rerun()

    for item_index in range(int(st.session_state[count_key])):
        seed = (
            seeds[item_index]
            if item_index < len(seeds)
            else {"criteria": dict(shared_defaults), "decision": "search"}
        )
        seed_criteria = seed.get("criteria") or {}
        with st.expander(f"Peça {item_index + 1}", expanded=True):
            item_decision = str(seed.get("decision") or "search")
            st.selectbox(
                "Situação da peça",
                options=["search", "ask", "handoff"],
                index=["search", "ask", "handoff"].index(item_decision),
                format_func=lambda value: {"search": "Pronta para buscar", "ask": "Precisa de informação", "handoff": "Atendimento humano"}[value],
                key=f"review_item_decision_{interaction_id}_{item_index}",
            )
            for key in REVIEW_CRITERIA_FIELDS:
                widget_key = f"review_item_{key}_{interaction_id}_{item_index}"
                if key in REVIEW_DIRECTION_OPTIONS:
                    choices = REVIEW_DIRECTION_OPTIONS[key]
                    default = str(seed_criteria.get(key) or "")
                    if default not in choices:
                        default = ""
                    st.selectbox(
                        REVIEW_FIELD_LABELS[key], options=list(choices),
                        index=list(choices).index(default),
                        format_func=lambda value, labels=choices: labels[value], key=widget_key,
                    )
                else:
                    st.text_input(
                        REVIEW_FIELD_LABELS[key],
                        value="" if seed_criteria.get(key) is None else str(seed_criteria.get(key)),
                        key=widget_key,
                    )
            item_missing = [
                value for value in (seed.get("missing_fields") or [])
                if value in REVIEW_CRITERIA_FIELDS
            ]
            st.multiselect(
                "Campos faltantes desta peça", options=list(REVIEW_CRITERIA_FIELDS),
                default=item_missing, format_func=lambda value: REVIEW_FIELD_LABELS[value],
                key=f"review_item_missing_{interaction_id}_{item_index}",
            )
            seed_question_key = seed.get("question_key") or ""
            st.selectbox(
                "Campo a perguntar", options=[""] + list(REVIEW_CRITERIA_FIELDS),
                index=([""] + list(REVIEW_CRITERIA_FIELDS)).index(seed_question_key)
                if seed_question_key in REVIEW_CRITERIA_FIELDS else 0,
                format_func=lambda value: "Nenhum" if not value else REVIEW_FIELD_LABELS[value],
                key=f"review_item_question_key_{interaction_id}_{item_index}",
            )
            st.text_input(
                "Pergunta desta peça", value=seed.get("question_prompt") or "",
                key=f"review_item_question_prompt_{interaction_id}_{item_index}",
            )
            st.text_area(
                "Opções desta peça — uma por linha",
                value="\n".join(str(value) for value in (seed.get("question_options") or [])),
                key=f"review_item_options_{interaction_id}_{item_index}",
            )
    predicted_missing = interaction.get("reviewed_missing_fields") or interaction.get("predicted_missing_fields") or []
    valid_default = [item for item in predicted_missing if item in REVIEW_CRITERIA_FIELDS]
    st.multiselect(
        "Campos que ainda estão faltando",
        options=list(REVIEW_CRITERIA_FIELDS),
        default=valid_default,
        format_func=lambda value: REVIEW_FIELD_LABELS[value],
        key=f"review_missing_{interaction_id}",
    )
    st.selectbox(
        "Campo da próxima pergunta (somente para Perguntar)",
        options=[""] + list(REVIEW_CRITERIA_FIELDS),
        index=([""] + list(REVIEW_CRITERIA_FIELDS)).index(
            interaction.get("reviewed_question_key") or predicted_question.get("key")
        ) if (interaction.get("reviewed_question_key") or predicted_question.get("key")) in REVIEW_CRITERIA_FIELDS else 0,
        format_func=lambda value: "Nenhum" if not value else REVIEW_FIELD_LABELS[value],
        key=f"review_question_key_{interaction_id}",
    )
    st.text_input(
        "Texto da próxima pergunta",
        value=interaction.get("reviewed_question_prompt") or predicted_question.get("prompt") or "",
        key=f"review_question_prompt_{interaction_id}",
    )
    st.text_area(
        "Opções da pergunta — uma por linha",
        value="\n".join(str(item) for item in (interaction.get("reviewed_question_options") or options or [])),
        key=f"review_question_options_{interaction_id}",
    )
    st.text_area(
        "Observações do avaliador",
        value=interaction.get("reviewed_notes") or "",
        key=f"review_notes_{interaction_id}",
    )
    save_col, discard_col = st.columns(2)
    if save_col.button("Salvar revisão", type="primary", use_container_width=True, key=f"save_review_{interaction_id}"):
        _submit_review(interaction)
    if discard_col.button("Descartar turno", use_container_width=True, key=f"discard_review_{interaction_id}"):
        _submit_review(interaction, discard=True)


def _render_review() -> None:
    flash = st.session_state.pop("review_flash", None)
    if flash:
        st.success(flash)

    top_left, top_middle, top_right = st.columns([2, 2, 1])
    with top_left:
        st.text_input("API de revisão", key="review_api_url")
    with top_middle:
        st.text_input("Nome do avaliador", key="reviewed_by")
    with top_right:
        mode_label = st.selectbox("Fila", ["Pendentes", "Concluídas"], key="review_queue_mode")

    status_value = "pending" if mode_label == "Pendentes" else "completed"
    result = _review_request("GET", "/review/conversations", params={"status": status_value, "limit": 100})
    if not result.get("ok"):
        st.error(result.get("error") or "Não foi possível consultar a fila de revisão.")
        return
    summaries = result["body"].get("items") or []
    if not summaries:
        st.info("Nenhuma conversa nesta fila.")
        return

    by_id = {str(item["conversation_id"]): item for item in summaries}
    selected_conversation = st.selectbox(
        "Conversa para avaliar",
        options=list(by_id),
        format_func=lambda value: _conversation_label(by_id[value]),
    )
    encoded = quote(selected_conversation, safe="")
    detail_result = _review_request("GET", f"/review/conversations/{encoded}")
    if not detail_result.get("ok"):
        st.error(detail_result.get("error") or "Não foi possível carregar a conversa.")
        return
    detail = detail_result["body"]
    interactions = detail.get("interactions") or []
    pending = [item for item in interactions if item.get("review_status") == "pending"]
    evaluated = [item for item in interactions if item.get("review_status") in {"reviewed", "discarded"}]
    selected_id: int | None = None
    selected_interaction: dict[str, Any] | None = None
    if pending:
        pending_by_id = {int(item["id"]): item for item in pending}
        selected_id = st.selectbox(
            "Turno pendente",
            options=list(pending_by_id),
            format_func=lambda value: f"#{value} — {str(pending_by_id[value].get('message_text') or '')[:90]}",
        )
        selected_interaction = pending_by_id[selected_id]

    timeline_col, form_col = st.columns([3, 2])
    with timeline_col:
        _render_review_timeline(interactions, selected_id)
    with form_col:
        if selected_interaction is not None:
            _render_review_form(selected_interaction)
            st.divider()
            if st.button("Descartar todos os turnos pendentes desta conversa", use_container_width=True):
                reviewer = str(st.session_state.reviewed_by or "").strip()
                if not reviewer:
                    st.error("Informe o nome do avaliador.")
                else:
                    discard_result = _review_request(
                        "POST",
                        f"/review/conversations/{encoded}/discard-pending",
                        payload={
                            "reviewed_by": reviewer,
                            "reviewed_notes": "Conversa descartada pela interface de revisão.",
                        },
                    )
                    if discard_result.get("ok"):
                        st.session_state.review_flash = "Conversa descartada e removida da fila de pendentes."
                        st.rerun()
                    else:
                        st.error(discard_result.get("error") or "Não foi possível descartar a conversa.")
        else:
            st.info("Esta conversa já foi totalmente avaliada. Ela está disponível apenas para consulta.")
        if evaluated:
            st.divider()
            evaluated_by_id = {int(item["id"]): item for item in evaluated}
            reopen_id = st.selectbox(
                "Turno já avaliado", options=list(evaluated_by_id),
                format_func=lambda value: f"#{value} — {str(evaluated_by_id[value].get('message_text') or '')[:80]}",
            )
            if st.button("Reabrir este turno para correção", use_container_width=True):
                reviewer = str(st.session_state.reviewed_by or "").strip()
                if not reviewer:
                    st.error("Informe o nome do avaliador.")
                else:
                    reopen_result = _review_request(
                        "POST", f"/review/interactions/{reopen_id}/reopen",
                        payload={"reviewed_by": reviewer, "reviewed_notes": "Reaberto pela interface para correção."},
                    )
                    if reopen_result.get("ok"):
                        st.session_state.review_queue_mode = "Pendentes"
                        st.session_state.review_flash = f"Turno #{reopen_id} reaberto para correção."
                        st.rerun()
                    else:
                        st.error(reopen_result.get("error") or "Não foi possível reabrir o turno.")


def main() -> None:
    st.set_page_config(
        page_title="Atendimento Autopecas",
        layout="wide",
    )
    _init_state()
    _render_sidebar()

    st.title("Atendimento Autopecas")
    section = st.radio(
        "Seção", ["Conversa", "Uso", "Revisão de IA"],
        horizontal=True, key="active_section", label_visibility="collapsed",
    )
    if section == "Conversa":
        _render_chat()
    elif section == "Uso":
        _render_usage()
    else:
        _render_review()


if __name__ == "__main__":
    main()
