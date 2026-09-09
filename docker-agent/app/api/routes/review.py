from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_pre_search_review_repository, require_review_api_key
from app.api.schemas.review import ReviewDiscardSubmission, ReviewReopenSubmission, ReviewSubmission
from app.core.domain.review_errors import (
    ReviewInteractionAlreadyEvaluatedError,
    ReviewInteractionNotFoundError,
    ReviewUnavailableError,
    ReviewValidationError,
)
from app.core.ports.pre_search_review_repository import PreSearchReviewRepositoryPort

router = APIRouter(prefix="/review", tags=["review"], dependencies=[Depends(require_review_api_key)])


def _run(operation: Any) -> Any:
    try:
        return operation()
    except ReviewInteractionAlreadyEvaluatedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ReviewInteractionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ReviewUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ReviewValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/conversations")
def list_review_conversations(
    review_status: Literal["pending", "completed", "all"] = Query("pending", alias="status"),
    limit: int = Query(50, ge=1, le=200),
    repository: PreSearchReviewRepositoryPort = Depends(get_pre_search_review_repository),
) -> dict[str, Any]:
    items = _run(lambda: repository.list_conversations(status=review_status, limit=limit))
    return {"status": review_status, "count": len(items), "items": items}


@router.get("/conversations/{conversation_id:path}")
def get_review_conversation(
    conversation_id: str,
    repository: PreSearchReviewRepositoryPort = Depends(get_pre_search_review_repository),
) -> dict[str, Any]:
    result = _run(lambda: repository.get_conversation(conversation_id=conversation_id))
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa nao encontrada.")
    return result


@router.put("/interactions/{interaction_id}")
def review_interaction(
    interaction_id: int,
    payload: ReviewSubmission,
    repository: PreSearchReviewRepositoryPort = Depends(get_pre_search_review_repository),
) -> dict[str, Any]:
    return _run(lambda: repository.review_interaction(
        interaction_id=interaction_id,
        decision=payload.decision,
        criteria=payload.criteria.model_dump(exclude_none=True),
        items=(
            [item.model_dump(exclude_none=True) for item in payload.items]
            if payload.items is not None
            else None
        ),
        missing_fields=payload.missing_fields,
        question_key=payload.question_key,
        question_prompt=payload.question_prompt,
        question_options=payload.question_options,
        reviewed_notes=payload.reviewed_notes,
        reviewed_by=payload.reviewed_by,
    ))


@router.post("/interactions/{interaction_id}/discard")
def discard_interaction(
    interaction_id: int,
    payload: ReviewDiscardSubmission,
    repository: PreSearchReviewRepositoryPort = Depends(get_pre_search_review_repository),
) -> dict[str, Any]:
    return _run(lambda: repository.discard_interaction(
        interaction_id=interaction_id,
        reviewed_notes=payload.reviewed_notes,
        reviewed_by=payload.reviewed_by,
    ))


@router.post("/conversations/{conversation_id:path}/discard-pending")
def discard_pending_conversation(
    conversation_id: str,
    payload: ReviewDiscardSubmission,
    repository: PreSearchReviewRepositoryPort = Depends(get_pre_search_review_repository),
) -> dict[str, Any]:
    return _run(lambda: repository.discard_pending_conversation(
        conversation_id=conversation_id,
        reviewed_notes=payload.reviewed_notes,
        reviewed_by=payload.reviewed_by,
    ))


@router.post("/interactions/{interaction_id}/reopen")
def reopen_interaction(
    interaction_id: int,
    payload: ReviewReopenSubmission,
    repository: PreSearchReviewRepositoryPort = Depends(get_pre_search_review_repository),
) -> dict[str, Any]:
    return _run(lambda: repository.reopen_interaction(
        interaction_id=interaction_id,
        reviewed_notes=payload.reviewed_notes,
        reviewed_by=payload.reviewed_by,
    ))
