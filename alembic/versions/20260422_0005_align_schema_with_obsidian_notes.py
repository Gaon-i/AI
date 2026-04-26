"""align schema with obsidian notes

Revision ID: 20260422_0005
Revises: 20260412_0004
Create Date: 2026-04-22 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260422_0005"
down_revision = "20260412_0004"
branch_labels = None
depends_on = None


LEGACY_DOCUMENT_VERSION = "v1"
LEGACY_EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_ANSWER_STATUS = ("PROCESSING", "SUCCESS", "NO_ANSWER", "ERROR")


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    _create_set_updated_at_function()

    op.create_table(
        "regulation_document",
        sa.Column("regulation_document_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.String(length=100), nullable=False),
        sa.Column("document_version", sa.String(length=50), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("dormitory", sa.String(length=50), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=255), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("regulation_document_id"),
        sa.UniqueConstraint(
            "document_id",
            "document_version",
            name="uq_regulation_document_doc_ver",
        ),
    )
    op.create_index(
        "idx_regulation_document_document_id",
        "regulation_document",
        ["document_id"],
    )
    op.create_index(
        "idx_regulation_document_document_version",
        "regulation_document",
        ["document_version"],
    )
    op.create_index("idx_regulation_document_category", "regulation_document", ["category"])
    op.create_index("idx_regulation_document_dormitory", "regulation_document", ["dormitory"])
    _create_updated_at_trigger("regulation_document")

    op.execute(
        sa.text(
            """
            INSERT INTO regulation_document (
                document_id,
                document_version,
                category,
                dormitory,
                title,
                content,
                source,
                source_url,
                source_type
            )
            SELECT DISTINCT
                document_id,
                :document_version,
                category,
                dormitory,
                title,
                content,
                source,
                source_url,
                source_type
            FROM regulation_chunk
            """
        ).bindparams(document_version=LEGACY_DOCUMENT_VERSION)
    )

    op.add_column(
        "regulation_chunk",
        sa.Column("regulation_document_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "regulation_chunk",
        sa.Column("document_version", sa.String(length=50), nullable=True),
    )
    op.add_column("regulation_chunk", sa.Column("chunk_hash", sa.String(length=255), nullable=True))
    op.add_column(
        "regulation_chunk",
        sa.Column("embedding_model", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "regulation_chunk",
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "regulation_chunk",
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )

    op.execute(
        sa.text(
            """
            UPDATE regulation_chunk rc
            SET document_version = :document_version,
                regulation_document_id = rd.regulation_document_id,
                chunk_hash = encode(digest(COALESCE(rc.chunk_text, ''), 'sha256'), 'hex'),
                embedding_model = :embedding_model
            FROM regulation_document rd
            WHERE rd.document_id = rc.document_id
              AND rd.document_version = :document_version
            """
        ).bindparams(
            document_version=LEGACY_DOCUMENT_VERSION,
            embedding_model=LEGACY_EMBEDDING_MODEL,
        )
    )

    op.alter_column("regulation_chunk", "regulation_document_id", nullable=False)
    op.alter_column("regulation_chunk", "document_version", nullable=False)
    op.create_foreign_key(
        "fk_regulation_chunk_document",
        "regulation_chunk",
        "regulation_document",
        ["regulation_document_id"],
        ["regulation_document_id"],
    )

    op.execute("DROP INDEX IF EXISTS ix_regulation_chunk_document_id")
    op.execute("DROP INDEX IF EXISTS ix_regulation_chunk_category")
    op.execute("DROP INDEX IF EXISTS ix_regulation_chunk_dormitory")
    op.execute("DROP INDEX IF EXISTS ix_regulation_chunk_source_type")

    op.create_index("idx_regulation_chunk_document_id", "regulation_chunk", ["regulation_document_id"])
    op.create_index("idx_regulation_chunk_document_version", "regulation_chunk", ["document_version"])
    op.create_index("idx_regulation_chunk_chunk_id", "regulation_chunk", ["chunk_id"])
    op.create_index("idx_regulation_chunk_is_active", "regulation_chunk", ["is_active"])

    op.drop_column("regulation_chunk", "document_id")
    op.drop_column("regulation_chunk", "category")
    op.drop_column("regulation_chunk", "dormitory")
    op.drop_column("regulation_chunk", "title")
    op.drop_column("regulation_chunk", "content")
    op.drop_column("regulation_chunk", "source")
    op.drop_column("regulation_chunk", "source_url")
    op.drop_column("regulation_chunk", "source_type")

    op.create_table(
        "chat_log",
        sa.Column("chat_log_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(length=100), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("rewritten_query", sa.Text(), nullable=True),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column(
            "answer_status",
            sa.Enum(
                *CHAT_ANSWER_STATUS,
                name="chat_answer_status",
                native_enum=False,
                create_constraint=True,
            ),
            server_default=sa.text("'PROCESSING'"),
            nullable=False,
        ),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("prompt_version", sa.String(length=50), nullable=True),
        sa.Column("retrieval_version", sa.String(length=50), nullable=True),
        sa.Column("response_time", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("chat_log_id"),
    )
    op.create_index("idx_chat_log_user_id", "chat_log", ["user_id"])
    op.create_index("idx_chat_log_session_id", "chat_log", ["session_id"])
    op.create_index("idx_chat_log_created_at", "chat_log", ["created_at"])
    op.create_index("idx_chat_log_answer_status", "chat_log", ["answer_status"])

    _create_updated_at_trigger("notice")

    op.create_table(
        "chat_retrieval_result",
        sa.Column("chat_retrieval_result_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("chat_log_id", sa.BigInteger(), nullable=False),
        sa.Column("regulation_chunk_id", sa.BigInteger(), nullable=False),
        sa.Column("document_id", sa.String(length=100), nullable=True),
        sa.Column("document_version", sa.String(length=50), nullable=True),
        sa.Column("chunk_id", sa.String(length=100), nullable=True),
        sa.Column("retrieval_rank", sa.Integer(), nullable=True),
        sa.Column("retrieval_score", sa.Numeric(10, 6), nullable=True),
        sa.Column("rerank_score", sa.Numeric(10, 6), nullable=True),
        sa.Column("retrieval_method", sa.String(length=50), nullable=True),
        sa.Column(
            "used_in_answer",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "selected_as_citation",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("citation_order", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["chat_log_id"], ["chat_log.chat_log_id"]),
        sa.ForeignKeyConstraint(["regulation_chunk_id"], ["regulation_chunk.regulation_chunk_id"]),
        sa.PrimaryKeyConstraint("chat_retrieval_result_id"),
        sa.UniqueConstraint(
            "chat_log_id",
            "regulation_chunk_id",
            name="uq_chat_retrieval_result_chat_chunk",
        ),
    )
    op.create_index(
        "idx_chat_retrieval_result_chat_log_id",
        "chat_retrieval_result",
        ["chat_log_id"],
    )
    op.create_index(
        "idx_chat_retrieval_result_regulation_chunk_id",
        "chat_retrieval_result",
        ["regulation_chunk_id"],
    )
    op.create_index(
        "idx_chat_retrieval_result_retrieval_rank",
        "chat_retrieval_result",
        ["retrieval_rank"],
    )
    op.create_index(
        "idx_chat_retrieval_result_document_id",
        "chat_retrieval_result",
        ["document_id"],
    )
    op.create_index(
        "idx_chat_retrieval_result_document_version",
        "chat_retrieval_result",
        ["document_version"],
    )
    op.create_index("idx_chat_retrieval_result_chunk_id", "chat_retrieval_result", ["chunk_id"])
    op.create_index(
        "idx_chat_retrieval_result_selected_as_citation",
        "chat_retrieval_result",
        ["selected_as_citation"],
    )
    op.create_index(
        "idx_chat_retrieval_result_retrieval_method",
        "chat_retrieval_result",
        ["retrieval_method"],
    )

    op.create_table(
        "chat_feedback",
        sa.Column("feedback_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("chat_log_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("feedback_type", sa.String(length=50), nullable=False),
        sa.Column("is_helpful", sa.Boolean(), nullable=True),
        sa.Column("rating", sa.SmallInteger(), nullable=True),
        sa.Column("reason_code", sa.String(length=50), nullable=True),
        sa.Column("feedback_comment", sa.Text(), nullable=True),
        sa.Column("feature_type", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("rating IS NULL OR rating BETWEEN 1 AND 5", name="chk_chat_feedback_rating"),
        sa.CheckConstraint(
            "feedback_type IN ('LIKE', 'DISLIKE', 'RATING')",
            name="chk_chat_feedback_type",
        ),
        sa.CheckConstraint(
            "reason_code IS NULL OR reason_code IN ("
            "'INCORRECT_ANSWER', 'BAD_CITATION', 'TOO_LONG', 'TOO_VAGUE', "
            "'OUTDATED_INFO', 'NO_SOURCE', 'OTHER'"
            ")",
            name="chk_chat_feedback_reason_code",
        ),
        sa.CheckConstraint(
            "feature_type IS NULL OR feature_type IN ('FAQ_CHAT', 'NOTICE_SUMMARY', 'COMPLAINT')",
            name="chk_chat_feedback_feature_type",
        ),
        sa.ForeignKeyConstraint(["chat_log_id"], ["chat_log.chat_log_id"]),
        sa.PrimaryKeyConstraint("feedback_id"),
    )
    op.create_index("idx_chat_feedback_chat_log_id", "chat_feedback", ["chat_log_id"])
    op.create_index("idx_chat_feedback_user_id", "chat_feedback", ["user_id"])
    op.create_index("idx_chat_feedback_is_helpful", "chat_feedback", ["is_helpful"])
    op.create_index("idx_chat_feedback_reason_code", "chat_feedback", ["reason_code"])
    op.create_index("idx_chat_feedback_feature_type", "chat_feedback", ["feature_type"])
    op.create_index("idx_chat_feedback_created_at", "chat_feedback", ["created_at"])

    op.create_table(
        "chat_admin_review",
        sa.Column("review_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("chat_log_id", sa.BigInteger(), nullable=False),
        sa.Column("reviewer_id", sa.BigInteger(), nullable=False),
        sa.Column("correctness_label", sa.String(length=50), nullable=False),
        sa.Column("citation_label", sa.String(length=50), nullable=True),
        sa.Column("root_cause", sa.String(length=50), nullable=True),
        sa.Column(
            "correction_required",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("corrected_answer", sa.Text(), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "correctness_label IN ('CORRECT', 'PARTIAL', 'INCORRECT')",
            name="chk_chat_admin_review_correctness",
        ),
        sa.CheckConstraint(
            "citation_label IS NULL OR citation_label IN ('APPROPRIATE', 'WEAK', 'WRONG', 'NONE')",
            name="chk_chat_admin_review_citation",
        ),
        sa.CheckConstraint(
            "root_cause IS NULL OR root_cause IN ("
            "'RETRIEVAL_FAIL', 'DOC_OUTDATED', 'NO_RELEVANT_DOC', "
            "'PROMPT_OVERGENERATION', 'QUESTION_AMBIGUOUS', 'MODEL_HALLUCINATION'"
            ")",
            name="chk_chat_admin_review_root_cause",
        ),
        sa.ForeignKeyConstraint(["chat_log_id"], ["chat_log.chat_log_id"]),
        sa.PrimaryKeyConstraint("review_id"),
    )
    op.create_index("idx_chat_admin_review_chat_log_id", "chat_admin_review", ["chat_log_id"])
    op.create_index("idx_chat_admin_review_reviewer_id", "chat_admin_review", ["reviewer_id"])
    op.create_index(
        "idx_chat_admin_review_correctness_label",
        "chat_admin_review",
        ["correctness_label"],
    )
    op.create_index(
        "idx_chat_admin_review_citation_label",
        "chat_admin_review",
        ["citation_label"],
    )
    op.create_index("idx_chat_admin_review_root_cause", "chat_admin_review", ["root_cause"])
    op.create_index("idx_chat_admin_review_created_at", "chat_admin_review", ["created_at"])

    op.create_table(
        "user_event_log",
        sa.Column("event_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("session_id", sa.String(length=100), nullable=False),
        sa.Column("chat_log_id", sa.BigInteger(), nullable=True),
        sa.Column("event_name", sa.String(length=50), nullable=False),
        sa.Column("feature_type", sa.String(length=50), nullable=True),
        sa.Column("event_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "event_name IN ("
            "'CHAT_STARTED', 'QUESTION_SUBMITTED', 'ANSWER_RENDERED', 'SOURCE_CLICKED', "
            "'NOTICE_ORIGINAL_CLICKED', 'FEEDBACK_SUBMITTED', 'NOTICE_VIEWED', "
            "'COMPLAINT_CREATED', 'RETURN_VISIT'"
            ")",
            name="chk_user_event_log_event_name",
        ),
        sa.ForeignKeyConstraint(["chat_log_id"], ["chat_log.chat_log_id"]),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index("idx_user_event_log_user_id", "user_event_log", ["user_id"])
    op.create_index("idx_user_event_log_session_id", "user_event_log", ["session_id"])
    op.create_index("idx_user_event_log_chat_log_id", "user_event_log", ["chat_log_id"])
    op.create_index("idx_user_event_log_event_name", "user_event_log", ["event_name"])
    op.create_index("idx_user_event_log_feature_type", "user_event_log", ["feature_type"])
    op.create_index("idx_user_event_log_created_at", "user_event_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_user_event_log_created_at", table_name="user_event_log")
    op.drop_index("idx_user_event_log_feature_type", table_name="user_event_log")
    op.drop_index("idx_user_event_log_event_name", table_name="user_event_log")
    op.drop_index("idx_user_event_log_chat_log_id", table_name="user_event_log")
    op.drop_index("idx_user_event_log_session_id", table_name="user_event_log")
    op.drop_index("idx_user_event_log_user_id", table_name="user_event_log")
    op.drop_table("user_event_log")

    op.drop_index("idx_chat_admin_review_created_at", table_name="chat_admin_review")
    op.drop_index("idx_chat_admin_review_root_cause", table_name="chat_admin_review")
    op.drop_index("idx_chat_admin_review_citation_label", table_name="chat_admin_review")
    op.drop_index("idx_chat_admin_review_correctness_label", table_name="chat_admin_review")
    op.drop_index("idx_chat_admin_review_reviewer_id", table_name="chat_admin_review")
    op.drop_index("idx_chat_admin_review_chat_log_id", table_name="chat_admin_review")
    op.drop_table("chat_admin_review")

    op.drop_index("idx_chat_feedback_created_at", table_name="chat_feedback")
    op.drop_index("idx_chat_feedback_feature_type", table_name="chat_feedback")
    op.drop_index("idx_chat_feedback_reason_code", table_name="chat_feedback")
    op.drop_index("idx_chat_feedback_is_helpful", table_name="chat_feedback")
    op.drop_index("idx_chat_feedback_user_id", table_name="chat_feedback")
    op.drop_index("idx_chat_feedback_chat_log_id", table_name="chat_feedback")
    op.drop_table("chat_feedback")

    op.drop_index(
        "idx_chat_retrieval_result_retrieval_method",
        table_name="chat_retrieval_result",
    )
    op.drop_index(
        "idx_chat_retrieval_result_selected_as_citation",
        table_name="chat_retrieval_result",
    )
    op.drop_index("idx_chat_retrieval_result_chunk_id", table_name="chat_retrieval_result")
    op.drop_index(
        "idx_chat_retrieval_result_document_version",
        table_name="chat_retrieval_result",
    )
    op.drop_index("idx_chat_retrieval_result_document_id", table_name="chat_retrieval_result")
    op.drop_index(
        "idx_chat_retrieval_result_retrieval_rank",
        table_name="chat_retrieval_result",
    )
    op.drop_index(
        "idx_chat_retrieval_result_regulation_chunk_id",
        table_name="chat_retrieval_result",
    )
    op.drop_index("idx_chat_retrieval_result_chat_log_id", table_name="chat_retrieval_result")
    op.drop_table("chat_retrieval_result")

    op.drop_index("idx_chat_log_answer_status", table_name="chat_log")
    op.drop_index("idx_chat_log_created_at", table_name="chat_log")
    op.drop_index("idx_chat_log_session_id", table_name="chat_log")
    op.drop_index("idx_chat_log_user_id", table_name="chat_log")
    op.drop_table("chat_log")
    op.execute("DROP TYPE IF EXISTS chat_answer_status")

    op.add_column("regulation_chunk", sa.Column("source_type", sa.Text(), nullable=True))
    op.add_column("regulation_chunk", sa.Column("source_url", sa.Text(), nullable=True))
    op.add_column("regulation_chunk", sa.Column("source", sa.Text(), nullable=True))
    op.add_column("regulation_chunk", sa.Column("content", sa.Text(), nullable=True))
    op.add_column("regulation_chunk", sa.Column("title", sa.Text(), nullable=True))
    op.add_column("regulation_chunk", sa.Column("dormitory", sa.Text(), nullable=True))
    op.add_column("regulation_chunk", sa.Column("category", sa.Text(), nullable=True))
    op.add_column("regulation_chunk", sa.Column("document_id", sa.String(length=100), nullable=True))

    op.execute(
        """
        UPDATE regulation_chunk rc
        SET document_id = rd.document_id,
            category = rd.category,
            dormitory = rd.dormitory,
            title = rd.title,
            content = rd.content,
            source = rd.source,
            source_url = rd.source_url,
            source_type = rd.source_type
        FROM regulation_document rd
        WHERE rd.regulation_document_id = rc.regulation_document_id
        """
    )

    op.alter_column("regulation_chunk", "document_id", nullable=False)
    op.alter_column("regulation_chunk", "title", nullable=False)
    op.alter_column("regulation_chunk", "content", nullable=False)
    op.alter_column("regulation_chunk", "source_type", nullable=False)

    op.drop_index("idx_regulation_chunk_is_active", table_name="regulation_chunk")
    op.drop_index("idx_regulation_chunk_chunk_id", table_name="regulation_chunk")
    op.drop_index("idx_regulation_chunk_document_version", table_name="regulation_chunk")
    op.drop_index("idx_regulation_chunk_document_id", table_name="regulation_chunk")
    op.drop_constraint("fk_regulation_chunk_document", "regulation_chunk", type_="foreignkey")
    op.drop_column("regulation_chunk", "created_at")
    op.drop_column("regulation_chunk", "is_active")
    op.drop_column("regulation_chunk", "embedding_model")
    op.drop_column("regulation_chunk", "chunk_hash")
    op.drop_column("regulation_chunk", "document_version")
    op.drop_column("regulation_chunk", "regulation_document_id")

    op.create_index("ix_regulation_chunk_document_id", "regulation_chunk", ["document_id"])
    op.create_index("ix_regulation_chunk_category", "regulation_chunk", ["category"])
    op.create_index("ix_regulation_chunk_dormitory", "regulation_chunk", ["dormitory"])
    op.create_index("ix_regulation_chunk_source_type", "regulation_chunk", ["source_type"])

    _drop_updated_at_trigger("regulation_document")
    op.drop_index("idx_regulation_document_dormitory", table_name="regulation_document")
    op.drop_index("idx_regulation_document_category", table_name="regulation_document")
    op.drop_index("idx_regulation_document_document_version", table_name="regulation_document")
    op.drop_index("idx_regulation_document_document_id", table_name="regulation_document")
    op.drop_table("regulation_document")
    _drop_updated_at_trigger("notice")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")


def _create_set_updated_at_function() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )


def _create_updated_at_trigger(table_name: str) -> None:
    op.execute(
        f"""
        DROP TRIGGER IF EXISTS trg_{table_name}_set_updated_at ON {table_name};
        CREATE TRIGGER trg_{table_name}_set_updated_at
        BEFORE UPDATE ON {table_name}
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at()
        """
    )


def _drop_updated_at_trigger(table_name: str) -> None:
    op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_set_updated_at ON {table_name}")
