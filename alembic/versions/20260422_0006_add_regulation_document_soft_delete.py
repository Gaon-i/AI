"""add regulation_document soft delete

Revision ID: 20260422_0006
Revises: 20260422_0005
Create Date: 2026-04-22 12:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260422_0006"
down_revision = "20260422_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "regulation_document",
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "regulation_document",
        sa.Column("deactivated_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "regulation_document",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "regulation_document",
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("regulation_document", "deleted_at")
    op.drop_column("regulation_document", "is_deleted")
    op.drop_column("regulation_document", "deactivated_at")
    op.drop_column("regulation_document", "is_active")
