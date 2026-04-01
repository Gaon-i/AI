import app.db.models  # noqa: F401
from app.db.base import Base
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
        "ix_regulation_chunk_category",
        "ix_regulation_chunk_dormitory",
        "ix_regulation_chunk_source_type",
    }


def test_regulation_chunk_columns_match_schema() -> None:
    table = Base.metadata.tables["regulation_chunk"]

    assert set(table.columns.keys()) == {
        "regulation_chunk_id",
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


def test_regulation_chunk_indexes_match_schema() -> None:
    table = Base.metadata.tables["regulation_chunk"]
    index_names = {index.name for index in table.indexes}

    assert index_names == {
        "ix_regulation_chunk_category",
        "ix_regulation_chunk_dormitory",
        "ix_regulation_chunk_source_type",
    }
