from uuid import uuid4

from sqlalchemy.orm import Session

from app.repositories.chat_session_repository import create_chat_session
from app.schemas.chat import ChatSessionCreateRequest
from app.schemas.chat import ChatSessionCreateResponse


def start_chat_session(
    db: Session,
    payload: ChatSessionCreateRequest,
) -> ChatSessionCreateResponse:
    chat_session = create_chat_session(
        db,
        session_id=str(uuid4()),
        user_id=payload.user_id,
        entry_point=payload.entry_point,
        is_returning_user=payload.is_returning_user,
        utm_source=payload.utm_source,
        utm_medium=payload.utm_medium,
        utm_campaign=payload.utm_campaign,
    )
    db.commit()
    db.refresh(chat_session)

    return ChatSessionCreateResponse(
        session_id=chat_session.session_id,
        user_id=chat_session.user_id,
        total_turns=chat_session.total_turns,
        started_at=chat_session.started_at,
        ended_at=chat_session.ended_at,
        last_activity_at=chat_session.last_activity_at,
        entry_point=chat_session.entry_point,
        is_returning_user=chat_session.is_returning_user,
        utm_source=chat_session.utm_source,
        utm_medium=chat_session.utm_medium,
        utm_campaign=chat_session.utm_campaign,
        created_at=chat_session.created_at,
    )
