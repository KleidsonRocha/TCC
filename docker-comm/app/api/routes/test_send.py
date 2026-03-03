import time
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import get_process_inbound_message_use_case, get_settings, require_api_key
from app.api.schemas import TestSendRequest, TestSendResponse
from app.core.domain.errors import (
    AgentBadResponseError,
    AgentTimeoutError,
    AgentUnavailableError,
    InvalidMessageError,
)
from app.core.domain.rules import build_internal_conversation_id, normalize_source
from app.core.usecases.process_inbound_message import ProcessInboundMessageUseCase

UNAVAILABLE_MESSAGE = "No momento nao consegui processar sua solicitacao. Tente novamente em instantes."

router = APIRouter(tags=["test"])


@router.post("/send", response_model=TestSendResponse)
async def send_test_message(
    payload: TestSendRequest,
    request: Request,
    _: None = Depends(require_api_key),
    use_case: ProcessInboundMessageUseCase = Depends(get_process_inbound_message_use_case),
) -> TestSendResponse:
    settings = get_settings(request)
    logger = request.app.state.logger
    if not settings.enable_test_endpoint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint disabled.")

    trace_id = str(uuid4())
    source = normalize_source(payload.source)
    incoming_conversation_id = (payload.conversation_id or "").strip()
    conversation_id = incoming_conversation_id or str(uuid4())
    internal_conversation_id = build_internal_conversation_id(source, conversation_id)
    request.state.trace_id = trace_id
    request.state.conversation_id = conversation_id
    request.state.internal_conversation_id = internal_conversation_id

    started_at = time.perf_counter()
    agent_status: int | None = None

    try:
        result = await use_case.execute(
            source=source,
            conversation_id=internal_conversation_id,
            text=payload.text,
            branch_id=payload.branch_id,
            trace_id=trace_id,
        )
        agent_status = result.agent_status_code
        return TestSendResponse(
            conversation_id=conversation_id,
            trace_id=result.trace_id,
            reply=result.reply,
            actions=result.actions,
            handoff=result.handoff,
            confidence=result.confidence,
        )
    except InvalidMessageError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AgentTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Timeout ao consultar o docker-agent.",
        ) from exc
    except AgentUnavailableError as exc:
        agent_status = exc.status_code
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=UNAVAILABLE_MESSAGE,
        ) from exc
    except AgentBadResponseError as exc:
        agent_status = exc.status_code
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=UNAVAILABLE_MESSAGE,
        ) from exc
    except Exception:
        logger.exception(
            "test_send_unhandled_error",
            extra={
                "trace_id": trace_id,
                "conversation_id": conversation_id,
                "internal_conversation_id": internal_conversation_id,
                "source": source,
                "endpoint": "/test/send",
            },
        )
        raise
    finally:
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.info(
            "test_send_processed",
            extra={
                "trace_id": trace_id,
                "conversation_id": conversation_id,
                "internal_conversation_id": internal_conversation_id,
                "source": source,
                "endpoint": "/test/send",
                "latency_ms": elapsed_ms,
                "agent_status": agent_status,
            },
        )
