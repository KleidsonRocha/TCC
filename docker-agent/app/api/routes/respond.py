import time

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.api.deps import get_process_agent_request_use_case, require_respond_gateway_key
from app.api.schemas.contract_v1 import AgentRequestV1, AgentResponseV1, HandoffPayload, ReplyPayload, ToolTracePayload
from app.core.domain.errors import (
    InvalidMessageError,
    PreSearchServiceUnavailableError,
    SearchPartsServiceUnavailableError,
    UnsupportedSchemaVersionError,
)
from app.core.usecases.process_agent_request import ProcessAgentRequestUseCase

router = APIRouter(tags=["agent"])


@router.post("/respond", response_model=AgentResponseV1)
async def respond(
    payload: AgentRequestV1,
    request: Request,
    x_agent_gateway_key: str | None = Header(default=None, alias="X-Agent-Gateway-Key"),
    use_case: ProcessAgentRequestUseCase = Depends(get_process_agent_request_use_case),
) -> AgentResponseV1:
    if payload.context and (
        payload.context.conversation_state is not None or payload.context.last_messages
    ):
        require_respond_gateway_key(
            request=request,
            x_agent_gateway_key=x_agent_gateway_key,
        )
    logger = request.app.state.logger
    started_at = time.perf_counter()
    response_status = status.HTTP_200_OK
    used_tools: list[str] = []
    stage_latency_ms: dict[str, float] = {}
    pre_search_path: str | None = None

    try:
        result = await use_case.execute(payload)
        used_tools = result.tool_trace.used_tools
        stage_latency_ms = dict(result.tool_trace.stage_latency_ms)
        pre_search_path = result.tool_trace.pre_search_path
        return AgentResponseV1(
            schema_version="1.0",
            trace_id=payload.trace_id,
            conversation_id=payload.conversation_id,
            reply=ReplyPayload(text=result.reply_text),
            actions=result.actions,
            handoff=HandoffPayload(required=result.handoff.required, reason=result.handoff.reason),
            confidence=result.confidence,
            tool_trace=ToolTracePayload(
                used_tools=result.tool_trace.used_tools,
                latency_ms=result.tool_trace.latency_ms,
                stage_latency_ms=result.tool_trace.stage_latency_ms,
                pre_search_path=result.tool_trace.pre_search_path,
            ),
            conversation_state=result.conversation_state,
            item_results=(
                [item.model_dump(exclude_none=True) for item in result.item_results]
                if result.item_results else None
            ),
        )
    except UnsupportedSchemaVersionError as exc:
        response_status = status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except InvalidMessageError as exc:
        response_status = status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PreSearchServiceUnavailableError as exc:
        response_status = status.HTTP_503_SERVICE_UNAVAILABLE
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except SearchPartsServiceUnavailableError as exc:
        response_status = status.HTTP_503_SERVICE_UNAVAILABLE
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        response_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        logger.exception(
            "respond_unhandled_error",
            extra={
                "trace_id": payload.trace_id,
                "conversation_id": payload.conversation_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar requisicao.",
        ) from exc
    finally:
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.info(
            "respond_processed",
            extra={
                "trace_id": payload.trace_id,
                "conversation_id": payload.conversation_id,
                "latency_ms": elapsed_ms,
                "status_code": response_status,
                "used_tools": used_tools,
                "stage_latency_ms": stage_latency_ms,
                "pre_search_path": pre_search_path,
            },
        )
