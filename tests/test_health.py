from fastapi.testclient import TestClient

from app.api import health as health_module


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_db_health(client: TestClient) -> None:
    response = client.get("/api/v1/health/db")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_db_health_returns_503_when_connection_fails(
    client: TestClient,
    monkeypatch,
) -> None:
    # DB 장애 상황을 강제로 만들어 헬스체크 실패 응답 규약을 검증합니다.
    def raise_connection_error() -> None:
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(health_module, "check_db_connection", raise_connection_error)

    response = client.get("/api/v1/health/db")

    assert response.status_code == 503
    assert response.json() == {"detail": "database unavailable"}
