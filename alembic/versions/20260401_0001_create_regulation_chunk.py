"""create regulation_chunk

Revision ID: 20260401_0001
Revises:
Create Date: 2026-04-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260401_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # pgvector 컬럼을 쓰기 전에 extension이 준비되도록 보장합니다.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 규정 검색용 청크 테이블과 필요한 인덱스를 생성합니다.
    op.create_table(
        "regulation_chunk",
        sa.Column("regulation_chunk_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.String(length=100), nullable=False),
        sa.Column("chunk_id", sa.String(length=100), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("dormitory", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(dim=1536), nullable=False),
        sa.UniqueConstraint("chunk_id", name="uq_regulation_chunk_chunk_id"),
    )
    op.create_index("ix_regulation_chunk_document_id", "regulation_chunk", ["document_id"])
    op.create_index("ix_regulation_chunk_category", "regulation_chunk", ["category"])
    op.create_index("ix_regulation_chunk_dormitory", "regulation_chunk", ["dormitory"])
    op.create_index("ix_regulation_chunk_source_type", "regulation_chunk", ["source_type"])


def downgrade() -> None:
    op.drop_index("ix_regulation_chunk_source_type", table_name="regulation_chunk")
    op.drop_index("ix_regulation_chunk_dormitory", table_name="regulation_chunk")
    op.drop_index("ix_regulation_chunk_category", table_name="regulation_chunk")
    op.drop_index("ix_regulation_chunk_document_id", table_name="regulation_chunk")
    op.drop_table("regulation_chunk")
