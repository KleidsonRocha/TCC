from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any
from uuid import uuid4

import httpx
import streamlit as st


DEFAULT_COMM_API_URL = "http://docker-comm:8000"
DEFAULT_SOURCE = "webchat"
DEFAULT_TIMEOUT_SECONDS = 60.0


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


def _headers() -> dict[str, str]:
    api_key = os.getenv("COMM_API_KEY") or os.getenv("API_KEY")
    if not api_key:
        return {}
    return {"X-API-Key": api_key}


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


def main() -> None:
    st.set_page_config(
        page_title="Atendimento Autopecas",
        layout="wide",
    )
    _init_state()
    _render_sidebar()

    st.title("Atendimento Autopecas")
    chat_tab, usage_tab = st.tabs(["Conversa", "Uso"])

    with chat_tab:
        _render_chat()

    with usage_tab:
        _render_usage()


if __name__ == "__main__":
    main()
