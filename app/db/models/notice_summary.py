from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import func
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.base import Base


class NoticeSummary(Base):
    __tablename__ = "notice_summary"

    notice_summary_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    notice_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("notice.notice_id"),
        nullable=False,
        unique=True,
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    target_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    schedule_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    caution_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generated_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
