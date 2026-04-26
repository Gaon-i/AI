from typing import Optional

from sqlalchemy import desc
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.chat_log import ChatLog
from app.db.models.chat_retrieval_result import ChatRetrievalResult
from app.db.models.chat_session import ChatSession


def get_chat_log_by_id(db: Session, chat_log_id: int) -> Optional[ChatLog]:
    statement = select(ChatLog).where(ChatLog.chat_log_id == chat_log_id)
    return db.execute(statement).scalar_one_or_none()


def list_recent_chat_sessions(db: Session, limit: int = 10) -> list[ChatSession]:
    statement = (
        select(ChatSession)
        .order_by(desc(ChatSession.last_activity_at), desc(ChatSession.started_at))
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
