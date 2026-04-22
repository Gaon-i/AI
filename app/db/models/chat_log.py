from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger
from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import func
from sqlalchemy import text
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.base import Base
from app.db.models.chat_enums import ChatAnswerStatus


class ChatLog(Base):
    __tablename__ = "chat_log"
    __table_args__ = (
        Index("idx_chat_log_user_id", "user_id"),
        Index("idx_chat_log_session_id", "session_id"),
        Index("idx_chat_log_created_at", "created_at"),
        Index("idx_chat_log_answer_status", "answer_status"),
    )

    chat_log_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    rewritten_query: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    answer_status: Mapped[ChatAnswerStatus] = mapped_column(
        Enum(
            ChatAnswerStatus,
            name="chat_answer_status",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
        ),
        nullable=False,
        server_default=text("'PROCESSING'"),
    )
    model_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    retrieval_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    response_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
