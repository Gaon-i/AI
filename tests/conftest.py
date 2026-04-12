import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.session import get_engine, get_session_factory


@pytest.fixture(autouse=True)
def test_environment(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    # 각 테스트 전후로 설정과 DB 캐시를 비워 import 순서에 따른 상태 누수를 막습니다.
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_NAME", "gaon-i-ai-test")
    monkeypatch.setenv("API_V1_PREFIX", "/api/v1")
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("ADMIN_API_TOKEN", "test-admin-token")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()

    yield

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()


@pytest.fixture
def client() -> TestClient:
    # env 설정 이후에 앱을 생성해서 실제 실행과 같은 초기화 흐름을 테스트합니다.
    from app.main import create_app

    return TestClient(create_app())
