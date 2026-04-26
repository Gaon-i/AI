"""관리자용 regulation_chunk 최초 적재 API의 요청/응답 계약을 검증하는 테스트 파일입니다."""

from fastapi.testclient import TestClient

from app.api import admin_regulation_chunk_ingestion as admin_regulation_chunk_ingestion_module
from app.core.error_codes import REGULATION_CHUNK_ALREADY_EXISTS
from app.core.exceptions import AppException
from app.schemas.regulation_chunk import RegulationChunkBulkIngestionResult
from app.schemas.regulation_chunk import RegulationChunkIngestionResult


def build_request_payload() -> dict:
    return {
        "regulation_document_id": 11,
    }


def build_admin_headers(token: str = "test-admin-token") -> dict[str, str]:
    # 관리자 API 테스트는 공통 토큰 헤더를 기본값으로 재사용합니다.
    return {"X-Admin-Token": token}


def build_bulk_request_payload(count: int = 2) -> dict:
    return {
        "regulation_document_ids": list(range(1, count + 1)),
    }


def test_ingest_regulation_chunks_from_document_api_returns_created_response(
    client: TestClient,
    monkeypatch,
) -> None:
    # API 계층 테스트에서는 실제 DB/임베딩 대신 service 반환값만 검증합니다.
    def fake_ingest_regulation_chunks_for_document(*_args, **_kwargs) -> RegulationChunkIngestionResult:
        return RegulationChunkIngestionResult(
            regulation_document_id=11,
            document_id="dorm-rule-001",
            document_version="2026.04",
            created_count=3,
        )

    monkeypatch.setattr(
        admin_regulation_chunk_ingestion_module,
        "ingest_regulation_chunks_for_document",
        fake_ingest_regulation_chunks_for_document,
    )

    response = client.post(
        "/api/v1/admin/regulation-chunks",
        json=build_request_payload(),
        headers=build_admin_headers(),
    )

    assert response.status_code == 201
    assert response.json() == {
        "status": 201,
        "message": "regulation chunks created from document",
        "data": {
            "regulation_document_id": 11,
            "document_id": "dorm-rule-001",
            "document_version": "2026.04",
            "created_count": 3,
        },
        "error_code": None,
    }


def test_ingest_regulation_chunks_from_document_api_returns_common_error_response(
    client: TestClient,
    monkeypatch,
) -> None:
    # service에서 도메인 예외를 던지면 전역 핸들러가 공통 에러 응답으로 변환해야 합니다.
    def raise_duplicate_chunk(*_args, **_kwargs) -> RegulationChunkIngestionResult:
        raise AppException(REGULATION_CHUNK_ALREADY_EXISTS)

    monkeypatch.setattr(
        admin_regulation_chunk_ingestion_module,
        "ingest_regulation_chunks_for_document",
        raise_duplicate_chunk,
    )

    response = client.post(
        "/api/v1/admin/regulation-chunks",
        json=build_request_payload(),
        headers=build_admin_headers(),
    )

    assert response.status_code == 409
    assert response.json() == {
        "status": 409,
        "message": "regulation chunk already exists",
        "data": None,
        "error_code": "REGULATION_CHUNK_ALREADY_EXISTS",
    }


def test_ingest_regulation_chunks_from_document_api_returns_validation_error_for_invalid_body(
    client: TestClient,
) -> None:
    payload = build_request_payload()
    payload["regulation_document_id"] = 0

    response = client.post(
        "/api/v1/admin/regulation-chunks",
        json=payload,
        headers=build_admin_headers(),
    )

    assert response.status_code == 422
    body = response.json()
    assert body["status"] == 422
    assert body["message"] == "request validation failed"
    assert body["error_code"] == "VALIDATION_ERROR"
    assert body["data"]["errors"]


def test_ingest_regulation_chunks_from_documents_bulk_api_returns_created_response(
    client: TestClient,
    monkeypatch,
) -> None:
    # 벌크 API도 단건과 동일한 공통 응답 포맷으로 성공 결과를 내려줘야 합니다.
    def fake_ingest_regulation_chunks_for_documents(*_args, **_kwargs) -> RegulationChunkBulkIngestionResult:
        return RegulationChunkBulkIngestionResult(
            created_document_count=2,
            items=[
                {"regulation_document_id": 1, "created_count": 3, "status": "created"},
                {"regulation_document_id": 2, "created_count": 2, "status": "created"},
            ],
        )

    monkeypatch.setattr(
        admin_regulation_chunk_ingestion_module,
        "ingest_regulation_chunks_for_documents",
        fake_ingest_regulation_chunks_for_documents,
    )

    response = client.post(
        "/api/v1/admin/regulation-chunks/bulk",
        json=build_bulk_request_payload(),
        headers=build_admin_headers(),
    )

    assert response.status_code == 201
    assert response.json() == {
        "status": 201,
        "message": "regulation chunks created from documents",
        "data": {
            "created_document_count": 2,
            "items": [
                {"regulation_document_id": 1, "created_count": 3, "status": "created"},
                {"regulation_document_id": 2, "created_count": 2, "status": "created"},
            ],
        },
        "error_code": None,
    }


def test_ingest_regulation_chunks_from_documents_bulk_api_returns_common_error_response(
    client: TestClient,
    monkeypatch,
) -> None:
    # 벌크 적재 중 하나라도 실패하면 service 예외가 그대로 공통 에러 응답으로 변환돼야 합니다.
    def raise_duplicate_chunk(*_args, **_kwargs) -> RegulationChunkBulkIngestionResult:
        raise AppException(REGULATION_CHUNK_ALREADY_EXISTS)

    monkeypatch.setattr(
        admin_regulation_chunk_ingestion_module,
        "ingest_regulation_chunks_for_documents",
        raise_duplicate_chunk,
    )

    response = client.post(
        "/api/v1/admin/regulation-chunks/bulk",
        json=build_bulk_request_payload(),
        headers=build_admin_headers(),
    )

    assert response.status_code == 409
    assert response.json() == {
        "status": 409,
        "message": "regulation chunk already exists",
        "data": None,
        "error_code": "REGULATION_CHUNK_ALREADY_EXISTS",
    }


def test_ingest_regulation_chunks_from_documents_bulk_api_rejects_more_than_twenty_items(
    client: TestClient,
) -> None:
    # 요청 개수 제한은 schema 단계에서 먼저 막아 서버와 외부 API 부하를 낮춥니다.
    response = client.post(
        "/api/v1/admin/regulation-chunks/bulk",
        json=build_bulk_request_payload(count=21),
        headers=build_admin_headers(),
    )

    assert response.status_code == 422
    body = response.json()
    assert body["status"] == 422
    assert body["message"] == "request validation failed"
    assert body["error_code"] == "VALIDATION_ERROR"
    assert body["data"]["errors"]


def test_admin_regulation_chunk_ingestion_api_requires_admin_token(client: TestClient) -> None:
    # 관리자 토큰이 없으면 관리자 API는 인증 실패로 막혀야 합니다.
    response = client.post("/api/v1/admin/regulation-chunks", json=build_request_payload())

    assert response.status_code == 401
    assert response.json() == {
        "status": 401,
        "message": "admin token required",
        "data": None,
        "error_code": "UNAUTHORIZED",
    }


def test_admin_regulation_chunk_ingestion_api_rejects_invalid_admin_token(client: TestClient) -> None:
    # 잘못된 토큰으로는 관리자 API를 호출할 수 없어야 합니다.
    response = client.post(
        "/api/v1/admin/regulation-chunks",
        json=build_request_payload(),
        headers=build_admin_headers(token="wrong-token"),
    )

    assert response.status_code == 403
    assert response.json() == {
        "status": 403,
        "message": "invalid admin api token",
        "data": None,
        "error_code": "ADMIN_API_TOKEN_INVALID",
    }


def test_admin_regulation_chunk_ingestion_bulk_api_requires_admin_token(client: TestClient) -> None:
    # router-level dependency가 bulk 엔드포인트에도 동일하게 적용되는지 확인합니다.
    response = client.post("/api/v1/admin/regulation-chunks/bulk", json=build_bulk_request_payload())

    assert response.status_code == 401
    assert response.json() == {
        "status": 401,
        "message": "admin token required",
        "data": None,
        "error_code": "UNAUTHORIZED",
    }


def test_admin_regulation_chunk_ingestion_api_returns_server_error_when_admin_token_setting_is_missing(
    client: TestClient,
    monkeypatch,
) -> None:
    # 서버 설정이 잘못된 경우도 공통 에러 응답으로 드러나도록 고정합니다.
    from app.core.config import get_settings

    monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)
    get_settings.cache_clear()

    response = client.post(
        "/api/v1/admin/regulation-chunks",
        json=build_request_payload(),
        headers=build_admin_headers(),
    )

    assert response.status_code == 500
    assert response.json() == {
        "status": 500,
        "message": "admin api token is missing",
        "data": None,
        "error_code": "ADMIN_API_TOKEN_MISSING",
    }
