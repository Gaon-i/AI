from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean
from sqlalchemy import CheckConstraint
from sqlalchemy import BigInteger
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import func
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.base import Base


class ChatSession(Base):
    __tablename__ = "chat_session"
    __table_args__ = (
        Index("idx_chat_session_user_id", "user_id"),
        Index("idx_chat_session_started_at", "started_at"),
        Index("idx_chat_session_ended_at", "ended_at"),
        Index("idx_chat_session_last_activity_at", "last_activity_at"),
        Index("idx_chat_session_entry_point", "entry_point"),
        Index("idx_chat_session_is_returning_user", "is_returning_user"),
        Index("idx_chat_session_utm_source", "utm_source"),
        Index("idx_chat_session_utm_medium", "utm_medium"),
        Index("idx_chat_session_utm_campaign", "utm_campaign"),
        CheckConstraint("total_turns >= 0", name="chk_chat_session_total_turns"),
        CheckConstraint(
            "entry_point IS NULL OR entry_point IN ('WEB', 'APP', 'NOTICE', 'FAQ')",
            name="chk_chat_session_entry_point",
        ),
    )

    session_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id"),
        nullable=True,
    )
    total_turns: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    entry_point: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_returning_user: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    utm_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    utm_medium: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    utm_campaign: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
