from datetime import datetime
from typing import List
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import func
from sqlalchemy import text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RegulationChunk(Base):
    # 생활관 규정 검색용 청크를 저장하는 핵심 테이블입니다.
    __tablename__ = "regulation_chunk"
    __table_args__ = (
        Index("idx_regulation_chunk_document_id", "regulation_document_id"),
        Index("idx_regulation_chunk_document_version", "document_version"),
        Index("idx_regulation_chunk_chunk_id", "chunk_id"),
        Index("idx_regulation_chunk_is_active", "is_active"),
    )

    regulation_chunk_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    regulation_document_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("regulation_document.regulation_document_id"),
        nullable=False,
    )
    document_version: Mapped[str] = mapped_column(String(50), nullable=False)
    chunk_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    keywords: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True)
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(1536), nullable=True)
    chunk_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    embedding_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
