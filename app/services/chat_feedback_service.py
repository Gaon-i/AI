from sqlalchemy.orm import Session

from app.core.error_codes import CHAT_LOG_NOT_FOUND
from app.core.exceptions import AppException
from app.repositories.chat_feedback_repository import create_chat_feedback
from app.repositories.chat_log_repository import get_chat_log_by_id
from app.schemas.chat import ChatFeedbackCreateRequest
from app.schemas.chat import ChatFeedbackCreateResponse


def create_feedback(
    db: Session,
    request: ChatFeedbackCreateRequest,
) -> ChatFeedbackCreateResponse:
    chat_log = get_chat_log_by_id(db, request.chat_log_id)
    if chat_log is None:
        raise AppException(CHAT_LOG_NOT_FOUND)

    feedback_type = "LIKE" if request.is_helpful else "DISLIKE"
    feedback = create_chat_feedback(
        db,
        chat_log_id=request.chat_log_id,
        user_id=chat_log.user_id,
        feedback_type=feedback_type,
        is_helpful=request.is_helpful,
        reason_code=request.reason_code,
        feedback_comment=request.feedback_comment,
    )
    db.commit()
    db.refresh(feedback)

    return ChatFeedbackCreateResponse(
        feedback_id=feedback.feedback_id,
        chat_log_id=feedback.chat_log_id,
        is_helpful=bool(feedback.is_helpful),
        feedback_type=feedback.feedback_type,
        reason_code=feedback.reason_code,
        feedback_comment=feedback.feedback_comment,
        created_at=feedback.created_at,
    )
