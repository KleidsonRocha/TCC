from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.config import Settings
from app.core.domain.review_errors import (
    ReviewInteractionAlreadyEvaluatedError,
    ReviewInteractionNotFoundError,
    ReviewUnavailableError,
    ReviewValidationError,
)
from app.core.domain.part_code import has_literal_part_code_evidence, normalize_part_code_candidate
from app.infra.postgres_conninfo import build_catalog_conninfo


class UnavailablePreSearchReviewRepository:
    @staticmethod
    def _raise() -> None:
        raise ReviewUnavailableError("A fila de revisao exige o banco de catalogo ativo.")

    def list_conversations(self, **_: Any) -> list[dict[str, Any]]:
        self._raise()

    def get_conversation(self, **_: Any) -> dict[str, Any] | None:
        self._raise()

    def review_interaction(self, **_: Any) -> dict[str, Any]:
        self._raise()

    def discard_interaction(self, **_: Any) -> dict[str, Any]:
        self._raise()

    def discard_pending_conversation(self, **_: Any) -> dict[str, Any]:
        self._raise()

    def reopen_interaction(self, **_: Any) -> dict[str, Any]:
        self._raise()


class PGPreSearchReviewRepository:
    def __init__(self, *, settings: Settings) -> None:
        self._conninfo = build_catalog_conninfo(settings)

    def list_conversations(self, *, status: str, limit: int) -> list[dict[str, Any]]:
        if status not in {"pending", "completed", "all"}:
            raise ValueError(f"Status de conversa invalido: {status}")
        having = {
            "pending": "COUNT(*) FILTER (WHERE review_status = 'pending') > 0",
            "completed": "COUNT(*) FILTER (WHERE review_status = 'pending') = 0",
            "all": "TRUE",
        }[status]
        with psycopg.connect(self._conninfo, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT
                        conversation_id,
                        MIN(created_at) AS started_at,
                        MAX(created_at) AS last_interaction_at,
                        COUNT(*) AS interaction_count,
                        COUNT(*) FILTER (WHERE review_status = 'pending') AS pending_count,
                        COUNT(*) FILTER (WHERE review_status = 'reviewed') AS reviewed_count,
                        COUNT(*) FILTER (WHERE review_status = 'promoted') AS promoted_count,
                        COUNT(*) FILTER (WHERE review_status = 'discarded') AS discarded_count,
                        MAX(review_priority_score) AS priority_score,
                        (ARRAY_AGG(message_text ORDER BY created_at DESC, id DESC))[1] AS latest_message,
                        BOOL_OR(llm_endpoint_used IS NOT NULL) AS contains_llm
                    FROM pre_search_review_interaction
                    GROUP BY conversation_id
                    HAVING {having}
                    ORDER BY
                        MAX(review_priority_score) DESC,
                        MAX(created_at) DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                return [dict(row) for row in cur.fetchall()]

    def get_conversation(self, *, conversation_id: str) -> dict[str, Any] | None:
        with psycopg.connect(self._conninfo, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM pre_search_review_interaction
                    WHERE conversation_id = %s
                    ORDER BY created_at ASC, id ASC
                    """,
                    (conversation_id,),
                )
                interactions = [dict(row) for row in cur.fetchall()]
                if not interactions:
                    return None
                cur.execute(
                    """
                    SELECT interaction_id, action, previous_status, snapshot, changed_by, notes, created_at
                    FROM pre_search_review_revision
                    WHERE interaction_id = ANY(%s)
                    ORDER BY created_at ASC, id ASC
                    """,
                    ([int(item["id"]) for item in interactions],),
                )
                history_by_id: dict[int, list[dict[str, Any]]] = {}
                for revision in cur.fetchall():
                    revision_row = dict(revision)
                    history_by_id.setdefault(int(revision_row.pop("interaction_id")), []).append(revision_row)
                for interaction in interactions:
                    interaction["review_history"] = history_by_id.get(int(interaction["id"]), [])
                progress = self._conversation_progress(cur, conversation_id=conversation_id)
        return {"conversation_id": conversation_id, "interactions": interactions, **progress}

    def review_interaction(
        self,
        *,
        interaction_id: int,
        decision: str,
        criteria: dict[str, Any],
        items: list[dict[str, Any]] | None,
        missing_fields: list[str],
        question_key: str | None,
        question_prompt: str | None,
        question_options: list[str] | None,
        reviewed_notes: str | None,
        reviewed_by: str,
    ) -> dict[str, Any]:
        if decision != "ask":
            question_key = None
            question_prompt = None
            question_options = None
        with psycopg.connect(self._conninfo, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                source = self._lock_pending_interaction(cur, interaction_id=interaction_id)
                part_code = normalize_part_code_candidate(criteria.get("part_code"))
                if part_code and not has_literal_part_code_evidence(
                    part_code,
                    message_text=str(source.get("message_text") or ""),
                    last_messages=source.get("last_messages") or [],
                ):
                    raise ReviewValidationError(
                        "O código da peça só pode entrar no dataset quando aparece literalmente em uma mensagem do usuário."
                    )
                if part_code:
                    criteria = {**criteria, "part_code": part_code}
                normalized_items = self._validate_review_items(items, source=source)
                cur.execute(
                    """
                    UPDATE pre_search_review_interaction
                    SET
                        review_status = 'reviewed',
                        reviewed_decision = %s,
                        reviewed_criteria = %s,
                        reviewed_items = %s,
                        reviewed_missing_fields = %s,
                        reviewed_question_key = %s,
                        reviewed_question_prompt = %s,
                        reviewed_question_options = %s,
                        reviewed_notes = %s,
                        reviewed_by = %s,
                        reviewed_at = NOW(),
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (
                        decision,
                        Jsonb(criteria),
                        Jsonb(normalized_items) if normalized_items is not None else None,
                        Jsonb(missing_fields),
                        question_key,
                        question_prompt,
                        Jsonb(question_options) if question_options is not None else None,
                        reviewed_notes,
                        reviewed_by,
                        interaction_id,
                    ),
                )
                self._record_revision(
                    cur,
                    interaction_id=interaction_id,
                    action="reviewed",
                    previous_status="pending",
                    snapshot={
                        "decision": decision,
                        "criteria": criteria,
                        "items": normalized_items,
                        "missing_fields": missing_fields,
                        "question_key": question_key,
                        "question_prompt": question_prompt,
                        "question_options": question_options,
                    },
                    changed_by=reviewed_by,
                    notes=reviewed_notes,
                )
                progress = self._conversation_progress(cur, conversation_id=source["conversation_id"])
            conn.commit()
        return {"interaction_id": interaction_id, "review_status": "reviewed", **progress}

    def discard_interaction(
        self, *, interaction_id: int, reviewed_notes: str | None, reviewed_by: str
    ) -> dict[str, Any]:
        with psycopg.connect(self._conninfo, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                source = self._lock_pending_interaction(cur, interaction_id=interaction_id)
                cur.execute(
                    """
                    UPDATE pre_search_review_interaction
                    SET review_status = 'discarded', reviewed_notes = %s, reviewed_by = %s,
                        reviewed_at = NOW(), updated_at = NOW()
                    WHERE id = %s
                    """,
                    (reviewed_notes, reviewed_by, interaction_id),
                )
                self._record_revision(
                    cur,
                    interaction_id=interaction_id,
                    action="discarded",
                    previous_status="pending",
                    snapshot={},
                    changed_by=reviewed_by,
                    notes=reviewed_notes,
                )
                progress = self._conversation_progress(cur, conversation_id=source["conversation_id"])
            conn.commit()
        return {"interaction_id": interaction_id, "review_status": "discarded", **progress}

    def discard_pending_conversation(
        self, *, conversation_id: str, reviewed_notes: str | None, reviewed_by: str
    ) -> dict[str, Any]:
        with psycopg.connect(self._conninfo, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM pre_search_review_interaction WHERE conversation_id = %s AND review_status = 'pending' FOR UPDATE",
                    (conversation_id,),
                )
                pending_ids = [int(row["id"]) for row in cur.fetchall()]
                cur.execute(
                    """
                    UPDATE pre_search_review_interaction
                    SET review_status = 'discarded', reviewed_notes = %s, reviewed_by = %s,
                        reviewed_at = NOW(), updated_at = NOW()
                    WHERE conversation_id = %s AND review_status = 'pending'
                    """,
                    (reviewed_notes, reviewed_by, conversation_id),
                )
                affected = cur.rowcount
                if affected == 0:
                    cur.execute(
                        "SELECT 1 FROM pre_search_review_interaction WHERE conversation_id = %s",
                        (conversation_id,),
                    )
                    if cur.fetchone() is None:
                        raise ReviewInteractionNotFoundError(
                            f"Conversa nao encontrada: {conversation_id}"
                        )
                for pending_id in pending_ids:
                    self._record_revision(
                        cur,
                        interaction_id=pending_id,
                        action="discarded",
                        previous_status="pending",
                        snapshot={},
                        changed_by=reviewed_by,
                        notes=reviewed_notes,
                    )
                progress = self._conversation_progress(cur, conversation_id=conversation_id)
            conn.commit()
        return {"discarded_count": affected, **progress}

    def reopen_interaction(
        self, *, interaction_id: int, reviewed_notes: str | None, reviewed_by: str
    ) -> dict[str, Any]:
        with psycopg.connect(self._conninfo, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM pre_search_review_interaction WHERE id = %s FOR UPDATE",
                    (interaction_id,),
                )
                row = cur.fetchone()
                if row is None:
                    raise ReviewInteractionNotFoundError(f"Interacao nao encontrada: {interaction_id}")
                source = dict(row)
                previous_status = str(source["review_status"])
                if previous_status == "pending":
                    raise ReviewInteractionAlreadyEvaluatedError(
                        interaction_id=interaction_id, review_status="pending"
                    )
                if previous_status == "promoted":
                    raise ReviewValidationError(
                        "Uma interacao promovida nao pode ser reaberta sem antes remover o registro do dataset."
                    )
                self._record_revision(
                    cur,
                    interaction_id=interaction_id,
                    action="reopened",
                    previous_status=previous_status,
                    snapshot=self._review_snapshot(source),
                    changed_by=reviewed_by,
                    notes=reviewed_notes,
                )
                cur.execute(
                    """
                    UPDATE pre_search_review_interaction
                    SET review_status = 'pending', reviewed_decision = NULL,
                        reviewed_criteria = NULL, reviewed_items = NULL,
                        reviewed_missing_fields = NULL, reviewed_question_key = NULL,
                        reviewed_question_prompt = NULL, reviewed_question_options = NULL,
                        reviewed_notes = NULL, reviewed_by = NULL, reviewed_at = NULL,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (interaction_id,),
                )
                progress = self._conversation_progress(cur, conversation_id=source["conversation_id"])
            conn.commit()
        return {"interaction_id": interaction_id, "review_status": "pending", **progress}

    @staticmethod
    def _lock_pending_interaction(cur: Any, *, interaction_id: int) -> dict[str, Any]:
        cur.execute(
            "SELECT * FROM pre_search_review_interaction WHERE id = %s FOR UPDATE",
            (interaction_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise ReviewInteractionNotFoundError(f"Interacao nao encontrada: {interaction_id}")
        source = dict(row)
        if source["review_status"] != "pending":
            raise ReviewInteractionAlreadyEvaluatedError(
                interaction_id=interaction_id,
                review_status=str(source["review_status"]),
            )
        return source

    @staticmethod
    def _review_snapshot(source: dict[str, Any]) -> dict[str, Any]:
        return {
            "reviewed_decision": source.get("reviewed_decision"),
            "reviewed_criteria": source.get("reviewed_criteria"),
            "reviewed_items": source.get("reviewed_items"),
            "reviewed_missing_fields": source.get("reviewed_missing_fields"),
            "reviewed_question_key": source.get("reviewed_question_key"),
            "reviewed_question_prompt": source.get("reviewed_question_prompt"),
            "reviewed_question_options": source.get("reviewed_question_options"),
            "reviewed_notes": source.get("reviewed_notes"),
            "reviewed_by": source.get("reviewed_by"),
            "reviewed_at": str(source.get("reviewed_at")) if source.get("reviewed_at") else None,
        }

    @staticmethod
    def _record_revision(
        cur: Any,
        *,
        interaction_id: int,
        action: str,
        previous_status: str,
        snapshot: dict[str, Any],
        changed_by: str,
        notes: str | None,
    ) -> None:
        cur.execute(
            """
            INSERT INTO pre_search_review_revision
                (interaction_id, action, previous_status, snapshot, changed_by, notes)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (interaction_id, action, previous_status, Jsonb(snapshot), changed_by, notes),
        )

    @staticmethod
    def _validate_review_items(
        items: list[dict[str, Any]] | None, *, source: dict[str, Any]
    ) -> list[dict[str, Any]] | None:
        if items is None:
            return None
        normalized: list[dict[str, Any]] = []
        for index, item in enumerate(items, start=1):
            criteria = dict(item.get("criteria") or {})
            part_code = normalize_part_code_candidate(criteria.get("part_code"))
            if part_code and not has_literal_part_code_evidence(
                part_code,
                message_text=str(source.get("message_text") or ""),
                last_messages=source.get("last_messages") or [],
            ):
                raise ReviewValidationError(
                    f"O codigo da peca do item {index} nao aparece literalmente em uma mensagem do usuario."
                )
            if part_code:
                criteria["part_code"] = part_code
            normalized.append({**item, "criteria": criteria})
        return normalized

    @staticmethod
    def _conversation_progress(cur: Any, *, conversation_id: str) -> dict[str, Any]:
        cur.execute(
            """
            SELECT
                COUNT(*) AS interaction_count,
                COUNT(*) FILTER (WHERE review_status = 'pending') AS pending_count,
                COUNT(*) FILTER (WHERE review_status = 'reviewed') AS reviewed_count,
                COUNT(*) FILTER (WHERE review_status = 'promoted') AS promoted_count,
                COUNT(*) FILTER (WHERE review_status = 'discarded') AS discarded_count
            FROM pre_search_review_interaction
            WHERE conversation_id = %s
            """,
            (conversation_id,),
        )
        counts = dict(cur.fetchone())
        counts["conversation_completed"] = int(counts["pending_count"]) == 0
        return counts


def review_repository_from_settings(*, settings: Settings) -> Any:
    if not settings.catalog_db_enabled:
        return UnavailablePreSearchReviewRepository()
    return PGPreSearchReviewRepository(settings=settings)
