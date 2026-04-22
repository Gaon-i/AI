from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger
from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy import UniqueConstraint
from sqlalchemy import func
from sqlalchemy import text
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.base import Base


class ChatRetrievalResult(Base):
    __tablename__ = "chat_retrieval_result"
    __table_args__ = (
        UniqueConstraint(
            "chat_log_id",
            "regulation_chunk_id",
            name="uq_chat_retrieval_result_chat_chunk",
        ),
        Index("idx_chat_retrieval_result_chat_log_id", "chat_log_id"),
        Index("idx_chat_retrieval_result_regulation_chunk_id", "regulation_chunk_id"),
        Index("idx_chat_retrieval_result_retrieval_rank", "retrieval_rank"),
        Index("idx_chat_retrieval_result_document_id", "document_id"),
        Index("idx_chat_retrieval_result_document_version", "document_version"),
        Index("idx_chat_retrieval_result_chunk_id", "chunk_id"),
        Index("idx_chat_retrieval_result_selected_as_citation", "selected_as_citation"),
        Index("idx_chat_retrieval_result_retrieval_method", "retrieval_method"),
    )

    chat_retrieval_result_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    chat_log_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chat_log.chat_log_id"),
        nullable=False,
    )
    regulation_chunk_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("regulation_chunk.regulation_chunk_id"),
        nullable=False,
    )
    document_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    document_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    chunk_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    retrieval_rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    retrieval_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)
    rerank_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)
    retrieval_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    used_in_answer: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    selected_as_citation: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    citation_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
