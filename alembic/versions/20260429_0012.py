"""align chat_session with obsidian table

Revision ID: 20260429_0012
Revises: 20260427_0011
Create Date: 2026-04-29 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260429_0012"
down_revision = "20260427_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chat_session", sa.Column("ended_at", sa.DateTime(timezone=False), nullable=True))
    op.add_column("chat_session", sa.Column("entry_point", sa.String(length=50), nullable=True))
    op.add_column(
        "chat_session",
        sa.Column("is_returning_user", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("chat_session", sa.Column("utm_source", sa.String(length=100), nullable=True))
    op.add_column("chat_session", sa.Column("utm_medium", sa.String(length=100), nullable=True))
    op.add_column("chat_session", sa.Column("utm_campaign", sa.String(length=100), nullable=True))
    op.add_column(
        "chat_session",
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now()),
    )

    op.create_check_constraint("chk_chat_session_total_turns", "chat_session", "total_turns >= 0")
    op.create_check_constraint(
        "chk_chat_session_entry_point",
        "chat_session",
        "entry_point IS NULL OR entry_point IN ('WEB', 'APP', 'NOTICE', 'FAQ')",
    )

    op.create_index("idx_chat_session_ended_at", "chat_session", ["ended_at"])
    op.create_index("idx_chat_session_entry_point", "chat_session", ["entry_point"])
    op.create_index("idx_chat_session_is_returning_user", "chat_session", ["is_returning_user"])
    op.create_index("idx_chat_session_utm_source", "chat_session", ["utm_source"])
    op.create_index("idx_chat_session_utm_medium", "chat_session", ["utm_medium"])
    op.create_index("idx_chat_session_utm_campaign", "chat_session", ["utm_campaign"])


def downgrade() -> None:
    op.drop_index("idx_chat_session_utm_campaign", table_name="chat_session")
    op.drop_index("idx_chat_session_utm_medium", table_name="chat_session")
    op.drop_index("idx_chat_session_utm_source", table_name="chat_session")
    op.drop_index("idx_chat_session_is_returning_user", table_name="chat_session")
    op.drop_index("idx_chat_session_entry_point", table_name="chat_session")
    op.drop_index("idx_chat_session_ended_at", table_name="chat_session")

    op.drop_constraint("chk_chat_session_entry_point", "chat_session", type_="check")
    op.drop_constraint("chk_chat_session_total_turns", "chat_session", type_="check")

    op.drop_column("chat_session", "created_at")
    op.drop_column("chat_session", "utm_campaign")
    op.drop_column("chat_session", "utm_medium")
    op.drop_column("chat_session", "utm_source")
    op.drop_column("chat_session", "is_returning_user")
    op.drop_column("chat_session", "entry_point")
    op.drop_column("chat_session", "ended_at")
