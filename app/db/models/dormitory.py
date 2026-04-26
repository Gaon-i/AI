from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger
from sqlalchemy import DateTime
from sqlalchemy import String
from sqlalchemy import func
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.base import Base


class Dormitory(Base):
    __tablename__ = "dormitory"

    dormitory_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    dormitory_name: Mapped[str] = mapped_column(String(100), nullable=False)
    campus_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    gender_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False),
        nullable=True,
        server_default=func.now(),
    )
