from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time_utils import get_current_utc_time
from app.db.models.chat_error_log import ChatErrorLog


def create_chat_error_log(
    db: Session,
    *,
    chat_log_id: int,
    session_id: Optional[str],
    error_type: str,
    error_message: str,
    error_detail: Optional[str],
    occurred_step: Optional[str],
) -> ChatErrorLog:
    chat_error_log = ChatErrorLog(
        chat_log_id=chat_log_id,
        session_id=session_id,
        error_type=error_type,
        error_message=error_message,
        error_detail=error_detail,
        occurred_step=occurred_step,
        created_at=get_current_utc_time(),
    )
    db.add(chat_error_log)
    db.flush()
    db.refresh(chat_error_log)
    return chat_error_log


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
