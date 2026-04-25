"""선호 신호 / 피드백 이력 조회·기록 저장소.

memory_service 가 `get_user_memory` tool 응답을 조립할 때 쓰는 SQL 계층.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_preference_signals(
    db: Session, user_ids: list[str]
) -> dict[str, dict[str, list[dict[str, str]] | list[str]]]:
    """preference_signals 에서 사용자별 선호를 꺼내 4 버킷으로 정리한다."""
    if not user_ids:
        return {}

    sql = text(
        """
        SELECT
          s.owner_id,
          s.signal_type,
          c.key           AS concept_key,
          c.label_ko      AS concept_label,
          s.target_restaurant_place_id,
          s.target_restaurant_name
        FROM preference_signals s
        LEFT JOIN concepts c ON c.id = s.concept_id
        WHERE s.owner_id::text = ANY(:ids)
        ORDER BY s.weight DESC NULLS LAST, s.updated_at DESC NULLS LAST
        """
    )
    rows = db.execute(sql, {"ids": [str(u) for u in user_ids]}).mappings().all()

    def _empty() -> dict:
        return {
            "likes": [],
            "dislikes": [],
            "likedRestaurants": [],
            "dislikedRestaurants": [],
        }

    out: dict[str, dict] = {}
    for row in rows:
        uid = str(row["owner_id"])
        slot = out.setdefault(uid, _empty())

        is_dislike = row["signal_type"] == "dislikes"
        is_like = row["signal_type"] == "likes"

        if row["concept_key"]:
            label = row["concept_label"] or row["concept_key"]
            if is_dislike and label not in slot["dislikes"]:
                slot["dislikes"].append(label)
            elif is_like and label not in slot["likes"]:
                slot["likes"].append(label)

        pid = row["target_restaurant_place_id"]
        if pid:
            entry = {"placeId": pid, "name": row["target_restaurant_name"] or ""}
            bucket = "dislikedRestaurants" if is_dislike else "likedRestaurants" if is_like else None
            if bucket and all(e["placeId"] != pid for e in slot[bucket]):
                slot[bucket].append(entry)

    return out


def get_recent_dislike_reasons(
    db: Session,
    user_ids: list[str],
    *,
    days: int = 30,
    limit_per_user: int = 20,
) -> dict[str, list[dict[str, Any]]]:
    """최근 👎 피드백 중 reason 이 있는 이벤트만 사용자별로 반환한다."""
    if not user_ids:
        return {}

    sql = text(
        """
        SELECT
          f.created_by_user_id,
          f.candidate_restaurant_place_id,
          f.reason_tags,
          f.free_text,
          f.created_at
        FROM feedback_events f
        WHERE f.created_by_user_id::text = ANY(:ids)
          AND f.verdict = 'disliked'
          AND (COALESCE(array_length(f.reason_tags, 1), 0) > 0 OR f.free_text IS NOT NULL)
          AND f.created_at >= now() - make_interval(days => :days)
        ORDER BY f.created_at DESC
        """
    )
    rows = db.execute(
        sql, {"ids": [str(u) for u in user_ids], "days": days}
    ).mappings().all()

    out: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        uid = str(row["created_by_user_id"])
        bucket = out.setdefault(uid, [])
        if len(bucket) >= limit_per_user:
            continue
        bucket.append(
            {
                "placeId": row["candidate_restaurant_place_id"],
                "reasonTags": list(row["reason_tags"] or []),
                "freeText": row["free_text"],
                "at": row["created_at"].date().isoformat() if row["created_at"] else None,
            }
        )
    return out


def upsert_preference_signal(
    db: Session,
    user_id: str,
    signal_type: str,
    *,
    concept_key: str | None = None,
    restaurant_place_id: str | None = None,
    restaurant_name: str | None = None,
    source: str = "agent",
) -> dict[str, Any]:
    """사용자 선호를 preference_signals 에 기록 (없으면 INSERT, 있으면 updated_at 만 갱신)."""
    if signal_type not in ("likes", "dislikes"):
        raise ValueError(f"signal_type 은 likes/dislikes 만 허용합니다 (got {signal_type!r})")
    if bool(concept_key) == bool(restaurant_place_id):
        raise ValueError("concept_key 와 restaurant_place_id 중 정확히 하나만 지정해야 합니다")

    concept_id: str | None = None
    target_label: str = ""

    if concept_key:
        sel = text("SELECT id, label_ko FROM concepts WHERE key = :k")
        row = db.execute(sel, {"k": concept_key}).mappings().first()
        if row:
            concept_id = str(row["id"])
            target_label = row["label_ko"] or concept_key
        else:
            ins = text(
                """
                INSERT INTO concepts (key, label_ko, concept_type)
                VALUES (:k, :k, 'food')
                RETURNING id
                """
            )
            new_id = db.execute(ins, {"k": concept_key}).scalar()
            concept_id = str(new_id)
            target_label = concept_key

    if restaurant_place_id:
        target_label = restaurant_name or restaurant_place_id

    check = text(
        """
        SELECT id FROM preference_signals
        WHERE owner_id = :uid AND signal_type = :st
          AND (
            (CAST(:concept_id AS uuid) IS NOT NULL AND concept_id = CAST(:concept_id AS uuid))
            OR (CAST(:place_id AS text) IS NOT NULL AND target_restaurant_place_id = :place_id)
          )
        LIMIT 1
        """
    )
    existing = db.execute(
        check,
        {
            "uid": user_id,
            "st": signal_type,
            "concept_id": concept_id,
            "place_id": restaurant_place_id,
        },
    ).mappings().first()

    if existing:
        db.execute(
            text("UPDATE preference_signals SET updated_at = now() WHERE id = :id"),
            {"id": str(existing["id"])},
        )
        db.commit()
        return {"action": "unchanged", "target": target_label}

    ins = text(
        """
        INSERT INTO preference_signals
          (owner_id, signal_type, concept_id,
           target_restaurant_place_id, target_restaurant_name, source)
        VALUES
          (:uid, :st, :concept_id, :place_id, :rname, :src)
        """
    )
    db.execute(
        ins,
        {
            "uid": user_id,
            "st": signal_type,
            "concept_id": concept_id,
            "place_id": restaurant_place_id,
            "rname": restaurant_name,
            "src": source,
        },
    )
    db.commit()
    return {"action": "inserted", "target": target_label}
