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
    assert "regulation_document" in Base.metadata.tables
    assert "regulation_chunk" in Base.metadata.tables
    assert "chat_log" in Base.metadata.tables
    assert "chat_retrieval_result" in Base.metadata.tables
    assert "chat_feedback" in Base.metadata.tables
    assert "chat_admin_review" in Base.metadata.tables
    assert "user_event_log" in Base.metadata.tables


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
        "source_type",
        "is_active",
        "deactivated_at",
        "is_deleted",
        "deleted_at",
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
