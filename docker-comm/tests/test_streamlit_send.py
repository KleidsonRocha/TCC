from types import SimpleNamespace

import httpx

from ui import streamlit_app


def test_streamlit_repeats_same_request_until_result_is_complete(monkeypatch) -> None:
    responses = [
        httpx.Response(200, json={"status": "processing", "reply": ""}),
        httpx.Response(200, json={"status": "completed", "reply": "Resposta pronta"}),
    ]
    sent_payloads = []

    class FakeClient:
        def __init__(self, timeout: float) -> None:
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def post(self, url, json, headers):
            _ = url, headers
            sent_payloads.append(json)
            return responses.pop(0)

    monkeypatch.setattr(streamlit_app.httpx, "Client", FakeClient)
    monkeypatch.setattr(streamlit_app.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(
        streamlit_app.st,
        "session_state",
        SimpleNamespace(
            comm_api_url="http://comm.local",
            source="webchat",
            conversation_id="room-1",
            branch_id=1,
        ),
    )

    result = streamlit_app._send_message(text="Freio Onix 2010")

    assert result["ok"] is True
    assert result["body"]["reply"] == "Resposta pronta"
    assert len(sent_payloads) == 2
    assert sent_payloads[0] == sent_payloads[1]
