"""create notice and notice_summary

Revision ID: 20260412_0004
Revises: 20260402_0003
Create Date: 2026-04-12 19:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260412_0004"
down_revision = "20260402_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notice",
        sa.Column("notice_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("posted_at", sa.DateTime(), nullable=False),
        sa.Column("collected_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("notice_id"),
        sa.UniqueConstraint("source_url"),
    )
    op.create_index("ix_notice_posted_at", "notice", ["posted_at"])

    op.create_table(
        "notice_summary",
        sa.Column("notice_summary_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("notice_id", sa.BigInteger(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("target_info", sa.Text(), nullable=True),
        sa.Column("schedule_info", sa.Text(), nullable=True),
        sa.Column("caution_info", sa.Text(), nullable=True),
        sa.Column("generated_model", sa.String(length=100), nullable=True),
        sa.Column("generated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["notice_id"], ["notice.notice_id"], name="fk_notice_summary_notice"),
        sa.PrimaryKeyConstraint("notice_summary_id"),
        sa.UniqueConstraint("notice_id"),
    )


def downgrade() -> None:
    op.drop_table("notice_summary")
    op.drop_index("ix_notice_posted_at", table_name="notice")
    op.drop_table("notice")
