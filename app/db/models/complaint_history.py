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


class ComplaintHistory(Base):
    __tablename__ = "complaint_history"
    __table_args__ = (
        Index("idx_complaint_history_complaint_id", "complaint_id"),
        Index("idx_complaint_history_admin_id", "admin_id"),
    )

    complaint_history_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    complaint_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("complaint.complaint_id"),
        nullable=False,
    )
    admin_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("admin.admin_id"), nullable=False)
    old_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    new_status: Mapped[str] = mapped_column(String(30), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False),
        nullable=True,
        server_default=func.now(),
    )
