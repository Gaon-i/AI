from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from typing import Optional

from sqlalchemy import desc
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.chat_error_log import ChatErrorLog
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
