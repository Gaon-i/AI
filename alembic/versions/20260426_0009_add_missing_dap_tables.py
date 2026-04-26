"""add missing dap tables

Revision ID: 20260426_0009
Revises: 20260426_0008
Create Date: 2026-04-26 00:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260426_0009"
down_revision = "20260426_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin",
        sa.Column("admin_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("login_id", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=100), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("admin_role", sa.String(length=30), server_default=sa.text("'STAFF'"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("admin_id"),
        sa.UniqueConstraint("login_id", name="uq_admin_login_id"),
    )

    op.create_table(
        "dormitory",
        sa.Column("dormitory_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("dormitory_name", sa.String(length=100), nullable=False),
        sa.Column("campus_name", sa.String(length=100), nullable=True),
        sa.Column("gender_type", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("dormitory_id"),
    )

    op.create_table(
        "email_verification",
        sa.Column("email_verification_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=100), nullable=False),
        sa.Column("verification_code", sa.String(length=20), nullable=False),
        sa.Column("purpose", sa.String(length=30), server_default=sa.text("'SIGNUP'"), nullable=False),
        sa.Column("expired_at", sa.DateTime(), nullable=False),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("email_verification_id"),
    )

    op.create_table(
        "faq",
        sa.Column("faq_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("source_title", sa.String(length=255), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("faq_id"),
    )

    op.create_table(
        "room",
        sa.Column("room_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("dormitory_id", sa.BigInteger(), nullable=False),
        sa.Column("building_name", sa.String(length=50), nullable=True),
        sa.Column("floor_no", sa.Integer(), nullable=True),
        sa.Column("room_no", sa.String(length=20), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["dormitory_id"], ["dormitory.dormitory_id"], name="fk_room_dormitory"),
        sa.PrimaryKeyConstraint("room_id"),
        sa.UniqueConstraint("dormitory_id", "building_name", "room_no", name="uq_room_dorm_building_room"),
    )
    op.create_index("idx_room_dormitory_id", "room", ["dormitory_id"])

    op.create_table(
        "user",
        sa.Column("user_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("student_no", sa.String(length=30), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("dormitory_id", sa.BigInteger(), nullable=False),
        sa.Column("room_id", sa.BigInteger(), nullable=False),
        sa.Column("email_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("account_status", sa.String(length=20), server_default=sa.text("'ACTIVE'"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["dormitory_id"], ["dormitory.dormitory_id"], name="fk_user_dormitory"),
        sa.ForeignKeyConstraint(["room_id"], ["room.room_id"], name="fk_user_room"),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("email", name="uq_user_email"),
    )

    op.create_table(
        "complaint",
        sa.Column("complaint_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'RECEIVED'"), nullable=False),
        sa.Column("queue_no", sa.Integer(), nullable=True),
        sa.Column("dormitory_id", sa.BigInteger(), nullable=False),
        sa.Column("room_id", sa.BigInteger(), nullable=False),
        sa.Column("assigned_admin_id", sa.BigInteger(), nullable=True),
        sa.Column("admin_comment", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.CheckConstraint("status IN ('RECEIVED', 'COMPLETED')", name="chk_complaint_status"),
        sa.ForeignKeyConstraint(["user_id"], ["user.user_id"], name="fk_complaint_user"),
        sa.ForeignKeyConstraint(["dormitory_id"], ["dormitory.dormitory_id"], name="fk_complaint_dormitory"),
        sa.ForeignKeyConstraint(["room_id"], ["room.room_id"], name="fk_complaint_room"),
        sa.ForeignKeyConstraint(["assigned_admin_id"], ["admin.admin_id"], name="fk_complaint_assigned_admin"),
        sa.PrimaryKeyConstraint("complaint_id"),
    )
    op.create_index("idx_complaint_user_id", "complaint", ["user_id"])
    op.create_index("idx_complaint_assigned_admin_id", "complaint", ["assigned_admin_id"])
    op.create_index("idx_complaint_status", "complaint", ["status"])
    op.create_index("idx_complaint_category", "complaint", ["category"])

    op.create_table(
        "complaint_image",
        sa.Column("complaint_image_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("complaint_id", sa.BigInteger(), nullable=False),
        sa.Column("file_url", sa.Text(), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=True),
        sa.Column("stored_name", sa.String(length=255), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["complaint_id"], ["complaint.complaint_id"], name="fk_complaint_image_complaint"),
        sa.PrimaryKeyConstraint("complaint_image_id"),
    )

    op.create_table(
        "complaint_history",
        sa.Column("complaint_history_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("complaint_id", sa.BigInteger(), nullable=False),
        sa.Column("admin_id", sa.BigInteger(), nullable=False),
        sa.Column("old_status", sa.String(length=30), nullable=True),
        sa.Column("new_status", sa.String(length=30), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["complaint_id"], ["complaint.complaint_id"], name="fk_complaint_history_complaint"),
        sa.ForeignKeyConstraint(["admin_id"], ["admin.admin_id"], name="fk_complaint_history_admin"),
        sa.PrimaryKeyConstraint("complaint_history_id"),
    )
    op.create_index("idx_complaint_history_complaint_id", "complaint_history", ["complaint_id"])
    op.create_index("idx_complaint_history_admin_id", "complaint_history", ["admin_id"])

    op.create_table(
        "system_log",
        sa.Column("system_log_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("log_level", sa.String(length=20), nullable=False),
        sa.Column("service_name", sa.String(length=100), nullable=True),
        sa.Column("api_endpoint", sa.String(length=255), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("error_stack", sa.Text(), nullable=True),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("ip_address", sa.String(length=50), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.user_id"], name="fk_system_log_user"),
        sa.PrimaryKeyConstraint("system_log_id"),
    )
    op.create_index("idx_system_log_log_level", "system_log", ["log_level"])
    op.create_index("idx_system_log_service_name", "system_log", ["service_name"])
    op.create_index("idx_system_log_created_at", "system_log", ["created_at"])

    op.create_table(
        "chat_error_log",
        sa.Column("error_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("chat_log_id", sa.BigInteger(), nullable=False),
        sa.Column("session_id", sa.String(length=100), nullable=True),
        sa.Column("error_type", sa.String(length=50), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("occurred_step", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.CheckConstraint(
            "error_type IN ("
            "'TIMEOUT', 'LLM_API_ERROR', 'RETRIEVAL_ERROR', "
            "'PROMPT_BUILD_ERROR', 'VALIDATION_ERROR', 'UNKNOWN_ERROR'"
            ")",
            name="chk_chat_error_log_error_type",
        ),
        sa.CheckConstraint(
            "occurred_step IS NULL OR occurred_step IN ("
            "'QUESTION_VALIDATION', 'QUERY_REWRITE', 'RETRIEVAL', "
            "'RERANK', 'ANSWER_GENERATION', 'RESPONSE_RENDERING'"
            ")",
            name="chk_chat_error_log_occurred_step",
        ),
        sa.ForeignKeyConstraint(["chat_log_id"], ["chat_log.chat_log_id"], name="fk_chat_error_log_chat_log"),
        sa.ForeignKeyConstraint(["session_id"], ["chat_session.session_id"], name="fk_chat_error_log_session"),
        sa.PrimaryKeyConstraint("error_id"),
    )
    op.create_index("idx_chat_error_log_chat_log_id", "chat_error_log", ["chat_log_id"])
    op.create_index("idx_chat_error_log_session_id", "chat_error_log", ["session_id"])
    op.create_index("idx_chat_error_log_error_type", "chat_error_log", ["error_type"])
    op.create_index("idx_chat_error_log_occurred_step", "chat_error_log", ["occurred_step"])
    op.create_index("idx_chat_error_log_created_at", "chat_error_log", ["created_at"])

    op.create_foreign_key(
        "fk_chat_log_session",
        "chat_log",
        "chat_session",
        ["session_id"],
        ["session_id"],
    )
    op.create_foreign_key(
        "fk_chat_log_user",
        "chat_log",
        "user",
        ["user_id"],
        ["user_id"],
    )
    op.create_foreign_key(
        "fk_chat_feedback_user",
        "chat_feedback",
        "user",
        ["user_id"],
        ["user_id"],
    )
    op.create_foreign_key(
        "fk_chat_admin_review_reviewer",
        "chat_admin_review",
        "admin",
        ["reviewer_id"],
        ["admin_id"],
    )
    op.create_foreign_key(
        "fk_user_event_log_user",
        "user_event_log",
        "user",
        ["user_id"],
        ["user_id"],
    )
    op.create_foreign_key(
        "fk_user_event_log_session",
        "user_event_log",
        "chat_session",
        ["session_id"],
        ["session_id"],
    )
    op.create_foreign_key(
        "fk_chat_session_user",
        "chat_session",
        "user",
        ["user_id"],
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_chat_session_user", "chat_session", type_="foreignkey")
    op.drop_constraint("fk_user_event_log_session", "user_event_log", type_="foreignkey")
    op.drop_constraint("fk_user_event_log_user", "user_event_log", type_="foreignkey")
    op.drop_constraint("fk_chat_admin_review_reviewer", "chat_admin_review", type_="foreignkey")
    op.drop_constraint("fk_chat_feedback_user", "chat_feedback", type_="foreignkey")
    op.drop_constraint("fk_chat_log_user", "chat_log", type_="foreignkey")
    op.drop_constraint("fk_chat_log_session", "chat_log", type_="foreignkey")

    op.drop_index("idx_chat_error_log_created_at", table_name="chat_error_log")
    op.drop_index("idx_chat_error_log_occurred_step", table_name="chat_error_log")
    op.drop_index("idx_chat_error_log_error_type", table_name="chat_error_log")
    op.drop_index("idx_chat_error_log_session_id", table_name="chat_error_log")
    op.drop_index("idx_chat_error_log_chat_log_id", table_name="chat_error_log")
    op.drop_table("chat_error_log")

    op.drop_index("idx_system_log_created_at", table_name="system_log")
    op.drop_index("idx_system_log_service_name", table_name="system_log")
    op.drop_index("idx_system_log_log_level", table_name="system_log")
    op.drop_table("system_log")

    op.drop_index("idx_complaint_history_admin_id", table_name="complaint_history")
    op.drop_index("idx_complaint_history_complaint_id", table_name="complaint_history")
    op.drop_table("complaint_history")

    op.drop_table("complaint_image")

    op.drop_index("idx_complaint_category", table_name="complaint")
    op.drop_index("idx_complaint_status", table_name="complaint")
    op.drop_index("idx_complaint_assigned_admin_id", table_name="complaint")
    op.drop_index("idx_complaint_user_id", table_name="complaint")
    op.drop_table("complaint")

    op.drop_table("user")

    op.drop_index("idx_room_dormitory_id", table_name="room")
    op.drop_table("room")

    op.drop_table("faq")
    op.drop_table("email_verification")
    op.drop_table("dormitory")
    op.drop_table("admin")
