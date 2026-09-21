import httpx

from app.core.domain.errors import AgentBadResponseError, AgentTimeoutError, AgentUnavailableError
from app.core.domain.models import AgentRequestPayload, AgentResponsePayload, ConversationState, HandoffInfo
from app.core.ports.agent_client import AgentClient


class HttpAgentClient(AgentClient):
    def __init__(
        self,
        *,
        agent_url: str,
        timeout_seconds: float,
        retry_count: int,
        gateway_api_key: str | None = None,
    ) -> None:
        self._agent_url = agent_url
        self._timeout_seconds = timeout_seconds
        self._max_attempts = max(1, retry_count + 1)
        self._gateway_api_key = gateway_api_key
        self._client = httpx.AsyncClient(timeout=self._timeout_seconds)

    async def send(
        self,
        payload: AgentRequestPayload,
        trace_id: str,
    ) -> tuple[AgentResponsePayload, int]:
        for attempt in range(self._max_attempts):
            try:
                headers = {"X-Trace-Id": trace_id}
                if self._gateway_api_key:
                    headers["X-Agent-Gateway-Key"] = self._gateway_api_key
                response = await self._client.post(
                    self._agent_url,
                    json=payload.model_dump(),
                    headers=headers,
                )
            except httpx.TimeoutException as exc:
                if attempt < self._max_attempts - 1:
                    continue
                raise AgentTimeoutError("Timeout while calling docker-agent.") from exc
            except httpx.RequestError as exc:
                if attempt < self._max_attempts - 1:
                    continue
                raise AgentUnavailableError("Could not reach docker-agent.") from exc

            if response.status_code in (502, 503) and attempt < self._max_attempts - 1:
                continue
            if response.status_code >= 500:
                raise AgentUnavailableError(
                    f"docker-agent returned {response.status_code}.",
                    status_code=response.status_code,
                )
            if response.status_code >= 400:
                raise AgentBadResponseError(
                    f"docker-agent returned {response.status_code}.",
                    status_code=response.status_code,
                )

            try:
                raw_payload = response.json()
            except ValueError as exc:
                raise AgentBadResponseError(
                    "docker-agent response is not valid JSON.",
                    status_code=response.status_code,
                ) from exc

            reply_text: str | object = ""
            if isinstance(raw_payload, dict):
                raw_reply = raw_payload.get("reply", "")
                if isinstance(raw_reply, dict):
                    reply_text = raw_reply.get("text", "")
                else:
                    reply_text = raw_reply
                if not reply_text:
                    reply_text = raw_payload.get("text", "")

            normalized = {
                "reply": reply_text,
                "actions": raw_payload.get("actions", []) if isinstance(raw_payload, dict) else [],
                "handoff": raw_payload.get("handoff", {"required": False, "reason": None})
                if isinstance(raw_payload, dict)
                else {"required": False, "reason": None},
                "confidence": raw_payload.get("confidence", 0.0) if isinstance(raw_payload, dict) else 0.0,
                "conversation_state": raw_payload.get("conversation_state")
                if isinstance(raw_payload, dict)
                else None,
                "item_results": raw_payload.get("item_results")
                if isinstance(raw_payload, dict)
                else None,
            }

            try:
                parsed = AgentResponsePayload(
                    reply=str(normalized["reply"]),
                    actions=list(normalized["actions"]),
                    handoff=HandoffInfo.model_validate(normalized["handoff"]),
                    confidence=float(normalized["confidence"] or 0.0),
                    conversation_state=(
                        ConversationState.model_validate(normalized["conversation_state"])
                        if normalized["conversation_state"]
                        else None
                    ),
                    item_results=(
                        list(normalized["item_results"])
                        if normalized["item_results"] else None
                    ),
                )
            except Exception as exc:
                raise AgentBadResponseError(
                    "docker-agent returned an invalid contract payload.",
                    status_code=response.status_code,
                ) from exc
            return parsed, response.status_code

        raise AgentUnavailableError("Unexpected retry flow while calling docker-agent.")

    async def close(self) -> None:
        await self._client.aclose()
