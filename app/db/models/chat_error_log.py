from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger
from sqlalchemy import CheckConstraint
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import func
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.base import Base


class ChatErrorLog(Base):
    __tablename__ = "chat_error_log"
    __table_args__ = (
        CheckConstraint(
            "error_type IN ("
            "'TIMEOUT', 'LLM_API_ERROR', 'RETRIEVAL_ERROR', "
            "'PROMPT_BUILD_ERROR', 'VALIDATION_ERROR', 'UNKNOWN_ERROR'"
            ")",
            name="chk_chat_error_log_error_type",
        ),
        CheckConstraint(
            "occurred_step IS NULL OR occurred_step IN ("
            "'QUESTION_VALIDATION', 'QUERY_REWRITE', 'RETRIEVAL', "
            "'RERANK', 'ANSWER_GENERATION', 'RESPONSE_RENDERING'"
            ")",
            name="chk_chat_error_log_occurred_step",
        ),
        Index("idx_chat_error_log_chat_log_id", "chat_log_id"),
        Index("idx_chat_error_log_session_id", "session_id"),
        Index("idx_chat_error_log_error_type", "error_type"),
        Index("idx_chat_error_log_occurred_step", "occurred_step"),
        Index("idx_chat_error_log_created_at", "created_at"),
    )

    error_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    chat_log_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chat_log.chat_log_id"), nullable=False)
    session_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        ForeignKey("chat_session.session_id"),
        nullable=True,
    )
    error_type: Mapped[str] = mapped_column(String(50), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    error_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    occurred_step: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False),
        nullable=True,
        server_default=func.now(),
    )
