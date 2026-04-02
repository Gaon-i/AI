"""restore document_id to regulation_chunk

Revision ID: 20260402_0003
Revises: 20260401_0002
Create Date: 2026-04-02 12:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260402_0003"
down_revision = "20260401_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # head 기준 스키마에 document_id 컬럼과 인덱스를 다시 복구합니다.
    # 이미 데이터가 있다면 올바른 원본 문서 ID를 알 수 없으므로 임의 값으로 채우지 않습니다.
    op.add_column(
        "regulation_chunk",
        sa.Column("document_id", sa.String(length=100), nullable=True),
    )
    connection = op.get_bind()
    row_count = connection.execute(sa.text("SELECT COUNT(*) FROM regulation_chunk")).scalar_one()
    if row_count > 0:
        raise RuntimeError(
            "document_id backfill is required before applying this migration to existing rows"
        )
    op.alter_column("regulation_chunk", "document_id", nullable=False)
    op.create_index("ix_regulation_chunk_document_id", "regulation_chunk", ["document_id"])


def downgrade() -> None:
    # 롤백 시에는 0002 상태와 동일하게 document_id를 다시 제거합니다.
    op.drop_index("ix_regulation_chunk_document_id", table_name="regulation_chunk")
    op.drop_column("regulation_chunk", "document_id")
