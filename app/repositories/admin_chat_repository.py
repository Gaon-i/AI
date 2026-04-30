from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from typing import Optional

from sqlalchemy import desc
from sqlalchemy import exists
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.chat_admin_review import ChatAdminReview
from app.db.models.chat_error_log import ChatErrorLog
from app.db.models.chat_feedback import ChatFeedback
from app.db.models.chat_enums import ChatAnswerStatus
from app.db.models.chat_log import ChatLog
from app.db.models.chat_retrieval_result import ChatRetrievalResult
from app.db.models.chat_session import ChatSession


def get_chat_log_by_id(db: Session, chat_log_id: int) -> Optional[ChatLog]:
    statement = select(ChatLog).where(ChatLog.chat_log_id == chat_log_id)
    return db.execute(statement).scalar_one_or_none()


def count_chat_sessions_by_started_date(db: Session, target_date: date) -> int:
    start_at = datetime.combine(target_date, time.min)
    end_at = start_at + timedelta(days=1)
    statement = (
        select(func.count())
        .select_from(ChatSession)
        .where(ChatSession.started_at >= start_at)
        .where(ChatSession.started_at < end_at)
    )
    return int(db.execute(statement).scalar_one())


def list_chat_sessions_by_started_date(
    db: Session,
    target_date: date,
    offset: int,
    limit: int,
) -> list[ChatSession]:
    start_at = datetime.combine(target_date, time.min)
    end_at = start_at + timedelta(days=1)
    statement = (
        select(ChatSession)
        .where(ChatSession.started_at >= start_at)
        .where(ChatSession.started_at < end_at)
        .order_by(desc(ChatSession.last_activity_at), desc(ChatSession.started_at))
        .offset(offset)
        .limit(limit)
    )
    return list(db.execute(statement).scalars().all())


def list_chat_retrieval_results_by_chat_log_id(
    db: Session,
    chat_log_id: int,
) -> list[ChatRetrievalResult]:
    statement = (
        select(ChatRetrievalResult)
        .where(ChatRetrievalResult.chat_log_id == chat_log_id)
        .order_by(
            ChatRetrievalResult.retrieval_rank.asc(),
            ChatRetrievalResult.chat_retrieval_result_id.asc(),
        )
    )
    return list(db.execute(statement).scalars().all())


def list_chat_error_logs_by_chat_log_id(
    db: Session,
    chat_log_id: int,
) -> list[ChatErrorLog]:
    statement = (
        select(ChatErrorLog)
        .where(ChatErrorLog.chat_log_id == chat_log_id)
        .order_by(ChatErrorLog.created_at.asc(), ChatErrorLog.error_id.asc())
    )
    return list(db.execute(statement).scalars().all())


def count_chat_review_queue_items(db: Session, reason: Optional[str] = None) -> int:
    statement = select(func.count(ChatLog.chat_log_id)).where(*_build_chat_review_queue_conditions(reason))
    return int(db.execute(statement).scalar_one())


def list_chat_review_queue_items(
    db: Session,
    *,
    reason: Optional[str],
    offset: int,
    limit: int,
) -> list[dict]:
    negative_feedback_count = _negative_feedback_count_subquery()
    latest_feedback_reason_code = _latest_feedback_reason_code_subquery()

    statement = (
        select(
            ChatLog,
            negative_feedback_count.label("negative_feedback_count"),
            latest_feedback_reason_code.label("latest_feedback_reason_code"),
        )
        .where(*_build_chat_review_queue_conditions(reason))
        .order_by(desc(ChatLog.created_at), desc(ChatLog.chat_log_id))
        .offset(offset)
        .limit(limit)
    )
    rows = db.execute(statement).all()
    return [
        {
            "chat_log": row[0],
            "negative_feedback_count": int(row.negative_feedback_count or 0),
            "latest_feedback_reason_code": row.latest_feedback_reason_code,
        }
        for row in rows
    ]


def _build_chat_review_queue_conditions(reason: Optional[str]) -> list:
    negative_feedback_exists = _negative_feedback_exists()
    unreviewed = ~exists().where(ChatAdminReview.chat_log_id == ChatLog.chat_log_id)

    if reason == "ERROR":
        reason_condition = ChatLog.answer_status == ChatAnswerStatus.ERROR
    elif reason == "NO_ANSWER":
        reason_condition = ChatLog.answer_status == ChatAnswerStatus.NO_ANSWER
    elif reason == "NEGATIVE_FEEDBACK":
        reason_condition = (
            negative_feedback_exists
            & ChatLog.answer_status.notin_([ChatAnswerStatus.ERROR, ChatAnswerStatus.NO_ANSWER])
        )
    else:
        reason_condition = or_(
            ChatLog.answer_status.in_([ChatAnswerStatus.ERROR, ChatAnswerStatus.NO_ANSWER]),
            negative_feedback_exists,
        )

    return [unreviewed, reason_condition]


def _negative_feedback_exists():
    return exists().where(
        ChatFeedback.chat_log_id == ChatLog.chat_log_id,
        ChatFeedback.is_helpful.is_(False),
    )


def _negative_feedback_count_subquery():
    return (
        select(func.count(ChatFeedback.feedback_id))
        .where(ChatFeedback.chat_log_id == ChatLog.chat_log_id)
        .where(ChatFeedback.is_helpful.is_(False))
        .correlate(ChatLog)
        .scalar_subquery()
    )


def _latest_feedback_reason_code_subquery():
    return (
        select(ChatFeedback.reason_code)
        .where(ChatFeedback.chat_log_id == ChatLog.chat_log_id)
        .where(ChatFeedback.is_helpful.is_(False))
        .order_by(desc(ChatFeedback.created_at), desc(ChatFeedback.feedback_id))
        .limit(1)
        .correlate(ChatLog)
        .scalar_subquery()
    )
