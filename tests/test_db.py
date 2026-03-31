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
    assert "document_chunks" in Base.metadata.tables
