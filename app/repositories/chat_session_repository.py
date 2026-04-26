from typing import Optional

from sqlalchemy.orm import Session

from app.db.models.chat_session import ChatSession


def create_chat_session(
    db: Session,
    session_id: str,
    user_id: Optional[int],
) -> ChatSession:
    chat_session = ChatSession(
        session_id=session_id,
        user_id=user_id,
        total_turns=0,
    )
    db.add(chat_session)
    db.flush()
    db.refresh(chat_session)
    return chat_session
