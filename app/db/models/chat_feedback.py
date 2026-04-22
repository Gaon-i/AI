from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger
from sqlalchemy import Boolean
from sqlalchemy import CheckConstraint
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import SmallInteger
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import func
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.base import Base


class ChatFeedback(Base):
    __tablename__ = "chat_feedback"
    __table_args__ = (
        CheckConstraint("rating IS NULL OR rating BETWEEN 1 AND 5", name="chk_chat_feedback_rating"),
        CheckConstraint(
            "feedback_type IN ('LIKE', 'DISLIKE', 'RATING')",
            name="chk_chat_feedback_type",
        ),
        CheckConstraint(
            "reason_code IS NULL OR reason_code IN ("
            "'INCORRECT_ANSWER', 'BAD_CITATION', 'TOO_LONG', 'TOO_VAGUE', "
            "'OUTDATED_INFO', 'NO_SOURCE', 'OTHER'"
            ")",
            name="chk_chat_feedback_reason_code",
        ),
        CheckConstraint(
            "feature_type IS NULL OR feature_type IN ("
            "'FAQ_CHAT', 'NOTICE_SUMMARY', 'COMPLAINT'"
            ")",
            name="chk_chat_feedback_feature_type",
        ),
        Index("idx_chat_feedback_chat_log_id", "chat_log_id"),
        Index("idx_chat_feedback_user_id", "user_id"),
        Index("idx_chat_feedback_is_helpful", "is_helpful"),
        Index("idx_chat_feedback_reason_code", "reason_code"),
        Index("idx_chat_feedback_feature_type", "feature_type"),
        Index("idx_chat_feedback_created_at", "created_at"),
    )

    feedback_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    chat_log_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chat_log.chat_log_id"),
        nullable=False,
    )
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    feedback_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_helpful: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    rating: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    reason_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    feedback_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    feature_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
