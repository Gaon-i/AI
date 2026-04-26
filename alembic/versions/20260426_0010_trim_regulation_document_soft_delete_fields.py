"""trim regulation_document soft delete fields

Revision ID: 20260426_0010
Revises: 20260426_0009
Create Date: 2026-04-26 01:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260426_0010"
down_revision = "20260426_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("regulation_document", "deleted_at")
    op.drop_column("regulation_document", "is_deleted")
    op.drop_column("regulation_document", "deactivated_at")


def downgrade() -> None:
    op.add_column("regulation_document", sa.Column("deactivated_at", sa.DateTime(), nullable=True))
    op.add_column(
        "regulation_document",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column("regulation_document", sa.Column("deleted_at", sa.DateTime(), nullable=True))
