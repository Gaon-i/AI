import app.db.models  # noqa: F401
from app.db.base import Base
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
    assert "regulation_chunk" in Base.metadata.tables


def test_regulation_chunk_columns_match_expected_schema() -> None:
    table = Base.metadata.tables["regulation_chunk"]

    assert set(table.columns.keys()) == {
        "regulation_chunk_id",
        "document_id",
        "chunk_id",
        "chunk_index",
        "category",
        "dormitory",
        "title",
        "content",
        "chunk_text",
        "keywords",
        "source",
        "source_url",
        "source_type",
        "embedding",
    }


def test_regulation_chunk_indexes_match_expected_schema() -> None:
    table = Base.metadata.tables["regulation_chunk"]
    index_names = {index.name for index in table.indexes}

    assert index_names == {
        "ix_regulation_chunk_document_id",
        "ix_regulation_chunk_category",
        "ix_regulation_chunk_dormitory",
        "ix_regulation_chunk_source_type",
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
