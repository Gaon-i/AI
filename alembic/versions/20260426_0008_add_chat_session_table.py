"""add chat_session table

Revision ID: 20260426_0008
Revises: 20260426_0007
Create Date: 2026-04-26 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260426_0008"
down_revision = "20260426_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_session",
        sa.Column("session_id", sa.String(length=100), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("total_turns", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now()),
        sa.Column("last_activity_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("session_id"),
    )
    op.create_index("idx_chat_session_user_id", "chat_session", ["user_id"])
    op.create_index("idx_chat_session_started_at", "chat_session", ["started_at"])
    op.create_index("idx_chat_session_last_activity_at", "chat_session", ["last_activity_at"])


def downgrade() -> None:
    op.drop_index("idx_chat_session_last_activity_at", table_name="chat_session")
    op.drop_index("idx_chat_session_started_at", table_name="chat_session")
    op.drop_index("idx_chat_session_user_id", table_name="chat_session")
    op.drop_table("chat_session")
