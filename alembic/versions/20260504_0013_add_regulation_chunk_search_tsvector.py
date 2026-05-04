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

BACKFILL_BATCH_SIZE = 1000


def upgrade() -> None:
    op.add_column(
        "regulation_chunk",
        sa.Column("search_tsvector", postgresql.TSVECTOR(), nullable=True),
    )

    bind = op.get_bind()
    last_processed_id = 0
    while True:
        result = bind.execute(
            sa.text(
                """
                WITH target_chunks AS (
                    SELECT regulation_chunk_id
                    FROM regulation_chunk
                    WHERE regulation_chunk_id > :last_processed_id
                    ORDER BY regulation_chunk_id
                    LIMIT :batch_size
                ),
                updated_chunks AS (
                    UPDATE regulation_chunk AS rc
                    SET search_tsvector = to_tsvector(
                        'simple',
                        COALESCE(rc.chunk_text, '') || ' ' ||
                        COALESCE(rd.content, '') || ' ' ||
                        COALESCE(
                            (
                                SELECT string_agg(keyword.value, ' ')
                                FROM jsonb_array_elements_text(rc.keywords) AS keyword(value)
                            ),
                            ''
                        )
                    )
                    FROM regulation_document AS rd
                    WHERE rd.regulation_document_id = rc.regulation_document_id
                      AND rc.regulation_chunk_id IN (
                          SELECT regulation_chunk_id FROM target_chunks
                      )
                    RETURNING rc.regulation_chunk_id
                )
                SELECT max(regulation_chunk_id) AS last_processed_id
                FROM updated_chunks
                """
            ),
            {
                "batch_size": BACKFILL_BATCH_SIZE,
                "last_processed_id": last_processed_id,
            },
        )
        next_last_processed_id = result.scalar()
        if next_last_processed_id is None:
            break
        last_processed_id = next_last_processed_id

    op.create_index(
        "idx_regulation_chunk_search_tsvector",
        "regulation_chunk",
        ["search_tsvector"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("idx_regulation_chunk_search_tsvector", table_name="regulation_chunk")
    op.drop_column("regulation_chunk", "search_tsvector")
