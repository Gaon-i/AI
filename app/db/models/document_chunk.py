from datetime import datetime
from typing import List
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[str] = mapped_column(String(255), index=True)
    chunk_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(1536), nullable=True)
    building_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
