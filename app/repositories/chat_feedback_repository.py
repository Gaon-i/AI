from typing import Optional

from sqlalchemy.orm import Session

from app.db.models.chat_feedback import ChatFeedback


def create_chat_feedback(
    db: Session,
    *,
    chat_log_id: int,
    user_id: Optional[int],
    feedback_type: str,
    is_helpful: bool,
    reason_code: Optional[str],
    feedback_comment: Optional[str],
    feature_type: str = "FAQ_CHAT",
) -> ChatFeedback:
    chat_feedback = ChatFeedback(
        chat_log_id=chat_log_id,
        user_id=user_id,
        feedback_type=feedback_type,
        is_helpful=is_helpful,
        reason_code=reason_code,
        feedback_comment=feedback_comment,
        feature_type=feature_type,
    )
    db.add(chat_feedback)
    db.flush()
    return chat_feedback
