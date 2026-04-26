from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.chat_enums import ChatAnswerStatus
from app.db.models.chat_log import ChatLog
from app.db.models.chat_session import ChatSession


def get_chat_session(db: Session, session_id: str) -> Optional[ChatSession]:
    statement = select(ChatSession).where(ChatSession.session_id == session_id)
    return db.execute(statement).scalar_one_or_none()


def create_chat_log(
    db: Session,
    *,
    session_id: str,
    user_id: Optional[int],
    question: str,
) -> ChatLog:
    chat_log = ChatLog(
        session_id=session_id,
        user_id=user_id,
        question=question,
        answer_status=ChatAnswerStatus.PROCESSING,
    )
    db.add(chat_log)
    db.flush()
    db.refresh(chat_log)
    return chat_log


def update_chat_log_result(
    db: Session,
    chat_log: ChatLog,
    *,
    answer_status: ChatAnswerStatus,
    answer: str,
    rewritten_query: Optional[str],
    model_name: Optional[str],
    prompt_version: Optional[str],
    retrieval_version: Optional[str],
    response_time: int,
) -> ChatLog:
    chat_log.answer_status = answer_status
    chat_log.answer = answer
    chat_log.rewritten_query = rewritten_query
    chat_log.model_name = model_name
    chat_log.prompt_version = prompt_version
    chat_log.retrieval_version = retrieval_version
    chat_log.response_time = response_time
    db.flush()
    db.refresh(chat_log)
    return chat_log


def touch_chat_session_activity(db: Session, chat_session: ChatSession) -> ChatSession:
    chat_session.total_turns += 1
    chat_session.last_activity_at = datetime.utcnow()
    db.flush()
    db.refresh(chat_session)
    return chat_session
