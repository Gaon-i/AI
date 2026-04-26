from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger
from sqlalchemy import CheckConstraint
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import func
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.base import Base


class UserEventLog(Base):
    __tablename__ = "user_event_log"
    __table_args__ = (
        CheckConstraint(
            "event_name IN ("
            "'CHAT_STARTED', 'QUESTION_SUBMITTED', 'ANSWER_RENDERED', 'SOURCE_CLICKED', "
            "'NOTICE_ORIGINAL_CLICKED', 'FEEDBACK_SUBMITTED', 'NOTICE_VIEWED', "
            "'COMPLAINT_CREATED', 'RETURN_VISIT'"
            ")",
            name="chk_user_event_log_event_name",
        ),
        Index("idx_user_event_log_user_id", "user_id"),
        Index("idx_user_event_log_session_id", "session_id"),
        Index("idx_user_event_log_chat_log_id", "chat_log_id"),
        Index("idx_user_event_log_event_name", "event_name"),
        Index("idx_user_event_log_feature_type", "feature_type"),
        Index("idx_user_event_log_created_at", "created_at"),
    )

    event_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id"),
        nullable=True,
    )
    session_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("chat_session.session_id"),
        nullable=False,
    )
    chat_log_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("chat_log.chat_log_id"),
        nullable=True,
    )
    event_name: Mapped[str] = mapped_column(String(50), nullable=False)
    feature_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    event_payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
