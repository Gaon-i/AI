"""add regulation chunk search tsvector

Revision ID: 20260504_0013
Revises: 20260429_0012
Create Date: 2026-05-04 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260504_0013"
down_revision = "20260429_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "regulation_chunk",
        sa.Column("search_tsvector", postgresql.TSVECTOR(), nullable=True),
    )

    op.execute(
        """
        UPDATE regulation_chunk AS rc
        SET search_tsvector = to_tsvector(
            'simple',
            COALESCE(rc.chunk_text, '') || ' ' ||
            COALESCE(rd.content, '') || ' ' ||
            COALESCE(rc.keywords::text, '')
        )
        FROM regulation_document AS rd
        WHERE rd.regulation_document_id = rc.regulation_document_id
        """
    )

    op.create_index(
        "idx_regulation_chunk_search_tsvector",
        "regulation_chunk",
        ["search_tsvector"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("idx_regulation_chunk_search_tsvector", table_name="regulation_chunk")
    op.drop_column("regulation_chunk", "search_tsvector")
