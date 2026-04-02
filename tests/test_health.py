from fastapi.testclient import TestClient

from app.api import health as health_module
from app.core.error_codes import DATABASE_UNAVAILABLE
from app.core.exceptions import AppException


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": 200,
        "message": "success",
        "data": {"status": "ok"},
        "error_code": None,
    }


def test_db_health(client: TestClient) -> None:
    response = client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {
        "status": 200,
        "message": "success",
        "data": {"status": "ok"},
        "error_code": None,
    }


def test_db_health_returns_503_when_connection_fails(
    client: TestClient,
    monkeypatch,
) -> None:
    # DB 장애 상황을 강제로 만들어 헬스체크 실패 응답 규약을 검증합니다.
    def raise_app_exception(_) -> None:
        raise AppException(DATABASE_UNAVAILABLE)

    monkeypatch.setattr(health_module, "get_db_health_response", raise_app_exception)

    response = client.get("/health/db")

    assert response.status_code == 503
    assert response.json() == {
        "status": 503,
        "message": "database unavailable",
        "data": None,
        "error_code": "DATABASE_UNAVAILABLE",
    }
