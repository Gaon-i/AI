"""drop document_id from regulation_chunk

Revision ID: 20260401_0002
Revises: 20260401_0001
Create Date: 2026-04-01 00:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260401_0002"
down_revision = "20260401_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 이미 수동으로 제거된 로컬 DB도 통과할 수 있게 조건부로 정리합니다.
    op.execute("DROP INDEX IF EXISTS ix_regulation_chunk_document_id")
    op.execute("ALTER TABLE regulation_chunk DROP COLUMN IF EXISTS document_id")


def downgrade() -> None:
    # 롤백 시에는 기존 초기 스키마와 동일하게 컬럼과 인덱스를 복구합니다.
    op.add_column(
        "regulation_chunk",
        sa.Column("document_id", sa.String(length=100), nullable=True),
    )
    op.execute("UPDATE regulation_chunk SET document_id = chunk_id WHERE document_id IS NULL")
    op.alter_column("regulation_chunk", "document_id", nullable=False)
    op.create_index("ix_regulation_chunk_document_id", "regulation_chunk", ["document_id"])
