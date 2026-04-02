from typing import List
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RegulationChunk(Base):
    # 생활관 규정 검색용 청크를 저장하는 핵심 테이블입니다.
    __tablename__ = "regulation_chunk"
    __table_args__ = (
        Index("ix_regulation_chunk_document_id", "document_id"),
        Index("ix_regulation_chunk_category", "category"),
        Index("ix_regulation_chunk_dormitory", "dormitory"),
        Index("ix_regulation_chunk_source_type", "source_type"),
    )

    regulation_chunk_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(String(100), nullable=False)
    chunk_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dormitory: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    keywords: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[List[float]] = mapped_column(Vector(1536), nullable=False)
