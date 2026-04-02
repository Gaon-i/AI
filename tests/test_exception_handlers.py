from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.error_codes import DATABASE_UNAVAILABLE
from app.core.exception_handlers import add_exception_handlers
from app.core.exceptions import AppException


class SampleRequest(BaseModel):
    name: str


def create_test_app() -> FastAPI:
    app = FastAPI()
    add_exception_handlers(app)

    @app.get("/app-exception")
    def raise_app_exception() -> None:
        raise AppException(DATABASE_UNAVAILABLE)

    @app.post("/validation")
    def validate_request(payload: SampleRequest) -> dict[str, str]:
        return {"name": payload.name}

    @app.get("/http-exception")
    def raise_http_exception() -> None:
        raise HTTPException(status_code=404, detail="resource not found")

    @app.get("/unexpected-exception")
    def raise_unexpected_exception() -> None:
        raise RuntimeError("unexpected failure")

    return app


def test_app_exception_returns_common_error_response() -> None:
    client = TestClient(create_test_app())

    response = client.get("/app-exception")

    assert response.status_code == 503
    assert response.json() == {
        "status": 503,
        "message": "database unavailable",
        "data": None,
        "error_code": "DATABASE_UNAVAILABLE",
    }


def test_validation_exception_returns_common_error_response() -> None:
    client = TestClient(create_test_app())

    response = client.post("/validation", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["status"] == 422
    assert body["message"] == "request validation failed"
    assert body["error_code"] == "VALIDATION_ERROR"
    assert body["data"]["errors"]


def test_http_exception_returns_common_error_response() -> None:
    client = TestClient(create_test_app())

    response = client.get("/http-exception")

    assert response.status_code == 404
    assert response.json() == {
        "status": 404,
        "message": "resource not found",
        "data": None,
        "error_code": "HTTP_ERROR",
    }


def test_unexpected_exception_returns_common_error_response() -> None:
    client = TestClient(create_test_app(), raise_server_exceptions=False)

    response = client.get("/unexpected-exception")

    assert response.status_code == 500
    assert response.json() == {
        "status": 500,
        "message": "internal server error",
        "data": None,
        "error_code": "INTERNAL_SERVER_ERROR",
    }
