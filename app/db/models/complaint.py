from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger
from sqlalchemy import CheckConstraint
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import func
from sqlalchemy import text
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.base import Base


class Complaint(Base):
    __tablename__ = "complaint"
    __table_args__ = (
        CheckConstraint("status IN ('RECEIVED', 'COMPLETED')", name="chk_complaint_status"),
        Index("idx_complaint_user_id", "user_id"),
        Index("idx_complaint_assigned_admin_id", "assigned_admin_id"),
        Index("idx_complaint_status", "status"),
        Index("idx_complaint_category", "category"),
    )

    complaint_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.user_id"), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=text("'RECEIVED'"),
    )
    queue_no: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    dormitory_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("dormitory.dormitory_id"),
        nullable=False,
    )
    room_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("room.room_id"), nullable=False)
    assigned_admin_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("admin.admin_id"),
        nullable=True,
    )
    admin_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False),
        nullable=True,
        server_default=func.now(),
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False),
        nullable=True,
        server_default=func.now(),
    )
