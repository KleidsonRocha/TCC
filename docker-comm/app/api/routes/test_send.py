import asyncio
import time
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import get_process_inbound_message_use_case, get_settings, require_api_key
from app.api.schemas import TestSendRequest, TestSendResponse
from app.config import Settings
from app.core.domain.errors import (
    AgentBadResponseError,
    AgentTimeoutError,
    AgentUnavailableError,
    InvalidMessageError,
)
from app.core.domain.rules import (
    build_internal_conversation_id,
    normalize_branch_id,
    normalize_source,
    validate_text,
)
from app.core.domain.response_stage import presentation_items, presentation_text, reply_with_options, response_stage
from app.core.usecases.process_inbound_message import ProcessInboundMessageUseCase
from app.infra.turn_store_redis import RedisTurnStore, turn_key

UNAVAILABLE_MESSAGE = "No momento nao consegui processar sua solicitacao. Tente novamente em instantes."

router = APIRouter(tags=["test"])


async def _renew_lease(
    *,
    store: RedisTurnStore,
    key: str,
    trace_id: str,
    settings: Settings,
    worker: asyncio.Task,
) -> None:
    while True:
        await asyncio.sleep(max(1, settings.turn_lease_seconds // 3))
        try:
            renewed = await store.renew(key, trace_id, settings.turn_lease_seconds)
        except Exception:
            worker.cancel()
            raise
        if not renewed:
            worker.cancel()
            return


async def _process_turn(
    *,
    store: RedisTurnStore,
    key: str,
    trace_id: str,
    source: str,
    conversation_id: str,
    internal_conversation_id: str,
    text: str,
    branch_id: int,
    use_case: ProcessInboundMessageUseCase,
    settings: Settings,
    logger,
) -> None:
    worker = asyncio.current_task()
    assert worker is not None
    renewal = asyncio.create_task(
        _renew_lease(
            store=store,
            key=key,
            trace_id=trace_id,
            settings=settings,
            worker=worker,
        )
    )
    started_at = time.perf_counter()
    try:
        try:
            result = await use_case.execute(
                source=source,
                conversation_id=internal_conversation_id,
                text=text,
                branch_id=branch_id,
                trace_id=trace_id,
            )
            items = presentation_items(result.actions)
            response = TestSendResponse(
                conversation_id=conversation_id,
                trace_id=trace_id,
                status="completed",
                stage=response_stage(handoff=result.handoff, actions=result.actions),
                reply=reply_with_options(result.reply, result.actions),
                actions=result.actions,
                items=items,
                items_text=presentation_text(items),
                handoff=result.handoff,
                confidence=result.confidence,
            )
            outcome = {
                "http_status": 200,
                "body": response.model_dump(mode="json"),
                "agent_status": result.agent_status_code,
            }
        except AgentTimeoutError:
            outcome = {"http_status": 504, "detail": "Timeout ao consultar o docker-agent."}
        except (AgentUnavailableError, AgentBadResponseError) as exc:
            outcome = {
                "http_status": 502,
                "detail": UNAVAILABLE_MESSAGE,
                "agent_status": exc.status_code,
            }
        except InvalidMessageError as exc:
            outcome = {"http_status": 400, "detail": str(exc)}
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(
                "test_send_unhandled_error",
                extra={"trace_id": trace_id, "conversation_id": conversation_id},
            )
            outcome = {"http_status": 500, "detail": UNAVAILABLE_MESSAGE}

        outcome["trace_id"] = trace_id
        stored = await store.finish(key, trace_id, outcome, settings.turn_result_ttl_seconds)
        logger.info(
            "test_send_turn_finished",
            extra={
                "trace_id": trace_id,
                "conversation_id": conversation_id,
                "source": source,
                "latency_ms": round((time.perf_counter() - started_at) * 1000, 2),
                "agent_status": outcome.get("agent_status"),
                "http_status": outcome["http_status"],
                "result_stored": stored,
            },
        )
    except asyncio.CancelledError:
        await store.release(key, trace_id)
        raise
    finally:
        renewal.cancel()
        await asyncio.gather(renewal, return_exceptions=True)


def _start_worker(app, **kwargs) -> None:
    task = asyncio.create_task(_process_turn(**kwargs))
    app.state.turn_tasks.add(task)

    def _finished(completed: asyncio.Task) -> None:
        app.state.turn_tasks.discard(completed)
        if not completed.cancelled():
            error = completed.exception()
            if error is not None:
                app.state.logger.error("test_send_worker_failed", exc_info=error)

    task.add_done_callback(_finished)


@router.post("/send", response_model=TestSendResponse)
async def send_test_message(
    payload: TestSendRequest,
    request: Request,
    _: None = Depends(require_api_key),
    use_case: ProcessInboundMessageUseCase = Depends(get_process_inbound_message_use_case),
) -> TestSendResponse:
    settings = get_settings(request)
    if not settings.enable_test_endpoint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint disabled.")

    store: RedisTurnStore = request.app.state.turn_store
    logger = request.app.state.logger
    incoming_conversation_id = (payload.conversation_id or "").strip()
    requested_trace_id = (payload.trace_id or "").strip()
    text = payload.text or ""
    poll_only = bool(requested_trace_id)
    if poll_only:
        trace = await store.get_trace(requested_trace_id)
        if trace is None:
            raise HTTPException(status_code=404, detail="Turno nao encontrado ou expirado.")
        key = trace["key"]
        conversation_id = trace["conversation_id"]
        source = trace["source"]
        internal_conversation_id = build_internal_conversation_id(source, conversation_id)
        branch_id = None
    else:
        source = normalize_source(payload.source)
        try:
            validate_text(text)
        except InvalidMessageError as exc:
            logger.warning(
                "test_send_invalid_text",
                extra={
                    "conversation_id": incoming_conversation_id or None,
                    "conversation_id_provided": bool(incoming_conversation_id),
                    "source": source,
                    "text_length": len(text),
                    "text_blank": not bool(text.strip()),
                    "endpoint": "/test/send",
                    "http_status": 400,
                },
            )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        conversation_id = incoming_conversation_id or str(uuid4())
        internal_conversation_id = build_internal_conversation_id(source, conversation_id)
        branch_id, _ = normalize_branch_id(payload.branch_id, settings.default_branch_id)
        key = turn_key(
            source=source,
            conversation_id=internal_conversation_id,
            branch_id=branch_id,
            text=text,
        )
    request.state.conversation_id = conversation_id
    request.state.internal_conversation_id = internal_conversation_id
    started_at = time.perf_counter()
    deadline = asyncio.get_running_loop().time() + settings.turn_wait_seconds
    trace_id: str | None = requested_trace_id or None
    result_source = "processing"
    http_status = 200
    try:
        while True:
            outcome = await store.get_result(key)
            if outcome is not None:
                result_source = "cached"
                http_status = outcome["http_status"]
                trace_id = outcome.get("trace_id")
                if http_status != 200:
                    raise HTTPException(status_code=http_status, detail=outcome["detail"])
                response = TestSendResponse.model_validate(outcome["body"])
                trace_id = response.trace_id
                return response

            owner = await store.get_owner(key)
            if owner is None:
                if poll_only:
                    raise HTTPException(status_code=409, detail="Turno interrompido ou expirado; reenvie a mensagem original.")
                candidate_trace_id = str(uuid4())
                if await store.claim(key, candidate_trace_id, settings.turn_lease_seconds):
                    # A previous worker may finish between the first cache read
                    # and this claim.
                    outcome = await store.get_result(key)
                    if outcome is not None:
                        await store.release(key, candidate_trace_id)
                        continue
                    trace_id = candidate_trace_id
                    result_source = "started"
                    try:
                        await store.bind_trace(
                            trace_id,
                            key,
                            conversation_id,
                            source,
                            settings.turn_result_ttl_seconds
                            + int(settings.agent_timeout_seconds) * (settings.agent_retry_count + 1)
                            + settings.turn_lease_seconds,
                        )
                    except Exception:
                        await store.release(key, trace_id)
                        raise
                    _start_worker(
                        request.app,
                        store=store,
                        key=key,
                        trace_id=trace_id,
                        source=source,
                        conversation_id=conversation_id,
                        internal_conversation_id=internal_conversation_id,
                        text=text,
                        branch_id=branch_id,
                        use_case=use_case,
                        settings=settings,
                        logger=logger,
                    )
                else:
                    owner = await store.get_owner(key)
            if owner is not None:
                trace_id = owner

            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                return TestSendResponse(
                    conversation_id=conversation_id,
                    trace_id=trace_id or str(uuid4()),
                    status="processing",
                    reply="",
                )
            await asyncio.sleep(min(0.5, remaining))
    finally:
        request.state.trace_id = trace_id
        logger.info(
            "test_send_processed",
            extra={
                "trace_id": trace_id,
                "conversation_id": conversation_id,
                "conversation_id_provided": bool(incoming_conversation_id),
                "poll_by_trace": poll_only,
                "internal_conversation_id": internal_conversation_id,
                "source": source,
                "text_length": len(text),
                "endpoint": "/test/send",
                "latency_ms": round((time.perf_counter() - started_at) * 1000, 2),
                "http_status": http_status,
                "result_source": result_source,
            },
        )
