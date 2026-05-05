import app.db.models  # noqa: F401
from app.db.base import Base
from app.db.models.chat_enums import ChatAnswerStatus
from app.db.models.notice import Notice
from app.db.session import check_db_connection, get_engine, get_session_factory


def test_db_session_factory_uses_test_database() -> None:
    session = get_session_factory()()
    try:
        assert session.bind is not None
        assert str(session.bind.url) == "sqlite+pysqlite:///:memory:"
    finally:
        session.close()


def test_db_connection_check_runs() -> None:
    check_db_connection()


def test_engine_uses_sqlite_for_test_environment() -> None:
    assert get_engine().dialect.name == "sqlite"


def test_document_chunk_model_is_registered_in_metadata() -> None:
    assert "admin" in Base.metadata.tables
    assert "user" in Base.metadata.tables
    assert "dormitory" in Base.metadata.tables
    assert "room" in Base.metadata.tables
    assert "email_verification" in Base.metadata.tables
    assert "faq" in Base.metadata.tables
    assert "regulation_document" in Base.metadata.tables
    assert "regulation_chunk" in Base.metadata.tables
    assert "complaint" in Base.metadata.tables
    assert "complaint_image" in Base.metadata.tables
    assert "complaint_history" in Base.metadata.tables
    assert "chat_session" in Base.metadata.tables
    assert "chat_log" in Base.metadata.tables
    assert "system_log" in Base.metadata.tables
    assert "chat_retrieval_result" in Base.metadata.tables
    assert "chat_feedback" in Base.metadata.tables
    assert "chat_admin_review" in Base.metadata.tables
    assert "user_event_log" in Base.metadata.tables
    assert "chat_error_log" in Base.metadata.tables


def test_regulation_document_columns_match_expected_schema() -> None:
    table = Base.metadata.tables["regulation_document"]

    assert set(table.columns.keys()) == {
        "regulation_document_id",
        "document_id",
        "document_version",
        "category",
        "dormitory",
        "title",
        "content",
        "source",
        "source_url",
        "keywords",
        "source_type",
        "is_active",
        "created_at",
        "updated_at",
    }


def test_regulation_chunk_columns_match_expected_schema() -> None:
    table = Base.metadata.tables["regulation_chunk"]

    assert set(table.columns.keys()) == {
        "regulation_chunk_id",
        "regulation_document_id",
        "document_version",
        "chunk_id",
        "chunk_index",
        "chunk_text",
        "keywords",
        "search_tsvector",
        "embedding",
        "chunk_hash",
        "embedding_model",
        "is_active",
        "created_at",
    }


def test_regulation_chunk_indexes_match_expected_schema() -> None:
    table = Base.metadata.tables["regulation_chunk"]
    index_names = {index.name for index in table.indexes}

    assert index_names == {
        "idx_regulation_chunk_document_id",
        "idx_regulation_chunk_document_version",
        "idx_regulation_chunk_chunk_id",
        "idx_regulation_chunk_is_active",
        "idx_regulation_chunk_search_tsvector",
    }


def test_chat_log_columns_match_expected_schema() -> None:
    table = Base.metadata.tables["chat_log"]

    assert set(table.columns.keys()) == {
        "chat_log_id",
        "session_id",
        "user_id",
        "question",
        "rewritten_query",
        "answer",
        "answer_status",
        "model_name",
        "prompt_version",
        "retrieval_version",
        "response_time",
        "created_at",
    }


def test_chat_log_answer_status_uses_expected_enum_values() -> None:
    table = Base.metadata.tables["chat_log"]
    answer_status_type = table.columns["answer_status"].type

    assert tuple(answer_status_type.enums) == tuple(status.value for status in ChatAnswerStatus)


def test_chat_session_columns_match_expected_schema() -> None:
    table = Base.metadata.tables["chat_session"]

    assert set(table.columns.keys()) == {
        "session_id",
        "user_id",
        "total_turns",
        "started_at",
        "ended_at",
        "last_activity_at",
        "entry_point",
        "is_returning_user",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "created_at",
    }


def test_chat_session_indexes_match_expected_schema() -> None:
    table = Base.metadata.tables["chat_session"]
    index_names = {index.name for index in table.indexes}

    assert index_names == {
        "idx_chat_session_user_id",
        "idx_chat_session_started_at",
        "idx_chat_session_ended_at",
        "idx_chat_session_last_activity_at",
        "idx_chat_session_entry_point",
        "idx_chat_session_is_returning_user",
        "idx_chat_session_utm_source",
        "idx_chat_session_utm_medium",
        "idx_chat_session_utm_campaign",
    }


def test_notice_models_are_registered_in_metadata() -> None:
    assert "notice" in Base.metadata.tables
    assert "notice_summary" in Base.metadata.tables


def test_notice_columns_match_expected_schema() -> None:
    table = Base.metadata.tables["notice"]

    assert set(table.columns.keys()) == {
        "notice_id",
        "title",
        "content",
        "source_url",
        "posted_at",
        "collected_at",
        "created_at",
        "updated_at",
    }
    assert str(table.columns["title"].type) == "VARCHAR(255)"


def test_notice_indexes_match_expected_schema() -> None:
    table = Base.metadata.tables["notice"]
    index_names = {index.name for index in table.indexes}

    assert index_names == {"ix_notice_posted_at"}


def test_notice_collected_at_uses_server_default_when_not_provided() -> None:
    notice = Notice(
        title="공지 제목",
        content="공지 본문",
        source_url="https://example.com/notices/collected-at-default",
        posted_at=None,
    )

    assert notice.collected_at is None
    assert notice.__table__.c.collected_at.server_default is not None
