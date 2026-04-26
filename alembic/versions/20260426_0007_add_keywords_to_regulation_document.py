"""add keywords to regulation_document

Revision ID: 20260426_0007
Revises: 20260422_0006
Create Date: 2026-04-26 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260426_0007"
down_revision = "20260422_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "regulation_document",
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("regulation_document", "keywords")
