from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import UniqueConstraint
from sqlalchemy import func
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.base import Base


class Room(Base):
    __tablename__ = "room"
    __table_args__ = (
        UniqueConstraint("dormitory_id", "building_name", "room_no", name="uq_room_dorm_building_room"),
        Index("idx_room_dormitory_id", "dormitory_id"),
    )

    room_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    dormitory_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("dormitory.dormitory_id"),
        nullable=False,
    )
    building_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    floor_no: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    room_no: Mapped[str] = mapped_column(String(20), nullable=False)
    capacity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False),
        nullable=True,
        server_default=func.now(),
    )
