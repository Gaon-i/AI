from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger
from sqlalchemy import Boolean
from sqlalchemy import CheckConstraint
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import func
from sqlalchemy import text
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.base import Base


class ChatAdminReview(Base):
    __tablename__ = "chat_admin_review"
    __table_args__ = (
        CheckConstraint(
            "correctness_label IN ('CORRECT', 'PARTIAL', 'INCORRECT')",
            name="chk_chat_admin_review_correctness",
        ),
        CheckConstraint(
            "citation_label IS NULL OR citation_label IN ("
            "'APPROPRIATE', 'WEAK', 'WRONG', 'NONE'"
            ")",
            name="chk_chat_admin_review_citation",
        ),
        CheckConstraint(
            "root_cause IS NULL OR root_cause IN ("
            "'RETRIEVAL_FAIL', 'DOC_OUTDATED', 'NO_RELEVANT_DOC', "
            "'PROMPT_OVERGENERATION', 'QUESTION_AMBIGUOUS', 'MODEL_HALLUCINATION'"
            ")",
            name="chk_chat_admin_review_root_cause",
        ),
        Index("idx_chat_admin_review_chat_log_id", "chat_log_id"),
        Index("idx_chat_admin_review_reviewer_id", "reviewer_id"),
        Index("idx_chat_admin_review_correctness_label", "correctness_label"),
        Index("idx_chat_admin_review_citation_label", "citation_label"),
        Index("idx_chat_admin_review_root_cause", "root_cause"),
        Index("idx_chat_admin_review_created_at", "created_at"),
    )

    review_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    chat_log_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chat_log.chat_log_id"),
        nullable=False,
    )
    reviewer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("admin.admin_id"),
        nullable=False,
    )
    correctness_label: Mapped[str] = mapped_column(String(50), nullable=False)
    citation_label: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    root_cause: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    correction_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    corrected_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
