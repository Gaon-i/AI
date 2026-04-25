"""add regulation_document document_type expression index

Revision ID: 20260427_0011
Revises: 20260426_0010
Create Date: 2026-04-27 03:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260427_0011"
down_revision = "20260426_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "idx_regulation_document_active_document_type_expr",
        "regulation_document",
        [sa.text("regexp_replace(document_id, '_[0-9]+$', '')")],
        unique=False,
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    op.drop_index(
        "idx_regulation_document_active_document_type_expr",
        table_name="regulation_document",
    )
