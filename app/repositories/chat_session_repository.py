from typing import Optional

from sqlalchemy.orm import Session

from app.core.time_utils import get_current_utc_time
from app.db.models.chat_session import ChatSession


def create_chat_session(
    db: Session,
    session_id: str,
    user_id: Optional[int],
    entry_point: Optional[str] = None,
    is_returning_user: bool = False,
    utm_source: Optional[str] = None,
    utm_medium: Optional[str] = None,
    utm_campaign: Optional[str] = None,
) -> ChatSession:
    current_time = get_current_utc_time()
    chat_session = ChatSession(
        session_id=session_id,
        user_id=user_id,
        total_turns=0,
        started_at=current_time,
        last_activity_at=current_time,
        entry_point=entry_point,
        is_returning_user=is_returning_user,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        created_at=current_time,
    )
    db.add(chat_session)
    db.flush()
    db.refresh(chat_session)
    return chat_session
