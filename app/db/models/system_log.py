from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import func
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.base import Base


class SystemLog(Base):
    __tablename__ = "system_log"
    __table_args__ = (
        Index("idx_system_log_log_level", "log_level"),
        Index("idx_system_log_service_name", "service_name"),
        Index("idx_system_log_created_at", "created_at"),
    )

    system_log_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    log_level: Mapped[str] = mapped_column(String(20), nullable=False)
    service_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    api_endpoint: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    error_stack: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("user.user_id"), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False),
        nullable=True,
        server_default=func.now(),
    )
