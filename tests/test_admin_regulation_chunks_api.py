"""관리자용 regulation_chunk 생성 API의 요청/응답 계약을 검증하는 테스트 파일입니다."""

from fastapi.testclient import TestClient

from app.api import admin_regulation_chunks as admin_regulation_chunks_module
from app.core.error_codes import REGULATION_CHUNK_ALREADY_EXISTS
from app.core.exceptions import AppException
from app.schemas.regulation_chunk import RegulationChunkBulkCreateResult
from app.schemas.regulation_chunk import RegulationChunkCreateResult
from app.schemas.regulation_chunk import RegulationChunkSourceType


def build_request_payload() -> dict:
    # 여러 API 테스트에서 공통으로 사용하는 정상 요청 바디입니다.
    return {
        "document_id": "dorm-rule-001",
        "document_version": "2026.04",
        "chunk_id": "dorm-rule-001-03",
        "chunk_index": 3,
        "category": "외박",
        "dormitory": "본관",
        "title": "외박 신청",
        "content": "외박은 사전에 신청해야 한다.",
        "keywords": ["외박", "신청"],
        "source": "생활관 규정집 2026",
        "source_url": "https://example.com/rule",
        "source_type": "official",
    }


def build_admin_headers(token: str = "test-admin-token") -> dict[str, str]:
    # 관리자 API 테스트는 공통 토큰 헤더를 기본값으로 재사용합니다.
    return {"X-Admin-Token": token}


def build_bulk_request_payload(count: int = 2) -> dict:
    # 벌크 API 테스트에서 여러 청크를 한 번에 보내기 위한 공통 요청 바디입니다.
    return {
        "items": [
            {
                "document_id": "dorm-rule-001",
                "document_version": "2026.04",
                "chunk_id": f"dorm-rule-001-{index:02d}",
                "chunk_index": index,
                "category": "외박",
                "dormitory": "본관",
                "title": f"외박 신청 {index}",
                "content": "외박은 사전에 신청해야 한다.",
                "keywords": ["외박", "신청"],
                "source": "생활관 규정집 2026",
                "source_url": "https://example.com/rule",
                "source_type": "official",
            }
            for index in range(1, count + 1)
        ]
    }


def test_create_regulation_chunk_api_returns_created_response(
    client: TestClient,
    monkeypatch,
) -> None:
    # API 계층 테스트에서는 실제 DB/임베딩 대신 service 반환값만 검증합니다.
    def fake_create_regulation_chunk_with_embedding(*_args, **_kwargs) -> RegulationChunkCreateResult:
        return RegulationChunkCreateResult(
            regulation_chunk_id=1,
            regulation_document_id=11,
            document_id="dorm-rule-001",
            document_version="2026.04",
            chunk_id="dorm-rule-001-03",
            chunk_index=3,
            source_type=RegulationChunkSourceType.OFFICIAL,
        )

    monkeypatch.setattr(
        admin_regulation_chunks_module,
        "create_regulation_chunk_with_embedding",
        fake_create_regulation_chunk_with_embedding,
    )

    response = client.post(
        "/api/v1/admin/regulation-chunks",
        json=build_request_payload(),
        headers=build_admin_headers(),
    )

    assert response.status_code == 201
    assert response.json() == {
        "status": 201,
        "message": "regulation chunk created",
        "data": {
            "regulation_chunk_id": 1,
            "regulation_document_id": 11,
            "document_id": "dorm-rule-001",
            "document_version": "2026.04",
            "chunk_id": "dorm-rule-001-03",
            "chunk_index": 3,
            "source_type": "official",
        },
        "error_code": None,
    }


def test_create_regulation_chunk_api_returns_common_error_response(
    client: TestClient,
    monkeypatch,
) -> None:
    # service에서 도메인 예외를 던지면 전역 핸들러가 공통 에러 응답으로 변환해야 합니다.
    def raise_duplicate_chunk(*_args, **_kwargs) -> RegulationChunkCreateResult:
        raise AppException(REGULATION_CHUNK_ALREADY_EXISTS)

    monkeypatch.setattr(
        admin_regulation_chunks_module,
        "create_regulation_chunk_with_embedding",
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


def test_create_regulation_chunk_api_returns_validation_error_for_invalid_body(
    client: TestClient,
) -> None:
    # 요청 바디가 schema를 통과하지 못하면 공통 validation 에러 응답이 내려와야 합니다.
    payload = build_request_payload()
    payload["document_id"] = "   "

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


def test_create_regulation_chunks_bulk_api_returns_created_response(
    client: TestClient,
    monkeypatch,
) -> None:
    # 벌크 API도 단건과 동일한 공통 응답 포맷으로 성공 결과를 내려줘야 합니다.
    def fake_create_regulation_chunks_with_embeddings(*_args, **_kwargs) -> RegulationChunkBulkCreateResult:
        return RegulationChunkBulkCreateResult(
            created_count=2,
            items=[
                {"chunk_id": "dorm-rule-001-01", "status": "created"},
                {"chunk_id": "dorm-rule-001-02", "status": "created"},
            ],
        )

    monkeypatch.setattr(
        admin_regulation_chunks_module,
        "create_regulation_chunks_with_embeddings",
        fake_create_regulation_chunks_with_embeddings,
    )

    response = client.post(
        "/api/v1/admin/regulation-chunks/bulk",
        json=build_bulk_request_payload(),
        headers=build_admin_headers(),
    )

    assert response.status_code == 201
    assert response.json() == {
        "status": 201,
        "message": "regulation chunks created",
        "data": {
            "created_count": 2,
            "items": [
                {"chunk_id": "dorm-rule-001-01", "status": "created"},
                {"chunk_id": "dorm-rule-001-02", "status": "created"},
            ],
        },
        "error_code": None,
    }


def test_create_regulation_chunks_bulk_api_returns_common_error_response(
    client: TestClient,
    monkeypatch,
) -> None:
    # 벌크 적재 중 하나라도 실패하면 service 예외가 그대로 공통 에러 응답으로 변환돼야 합니다.
    def raise_duplicate_chunk(*_args, **_kwargs) -> RegulationChunkBulkCreateResult:
        raise AppException(REGULATION_CHUNK_ALREADY_EXISTS)

    monkeypatch.setattr(
        admin_regulation_chunks_module,
        "create_regulation_chunks_with_embeddings",
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


def test_create_regulation_chunks_bulk_api_rejects_more_than_twenty_items(
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


def test_admin_regulation_chunks_api_requires_admin_token(client: TestClient) -> None:
    # 관리자 토큰이 없으면 관리자 API는 인증 실패로 막혀야 합니다.
    response = client.post("/api/v1/admin/regulation-chunks", json=build_request_payload())

    assert response.status_code == 401
    assert response.json() == {
        "status": 401,
        "message": "admin token required",
        "data": None,
        "error_code": "UNAUTHORIZED",
    }


def test_admin_regulation_chunks_api_rejects_invalid_admin_token(client: TestClient) -> None:
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


def test_admin_regulation_chunks_bulk_api_requires_admin_token(client: TestClient) -> None:
    # router-level dependency가 bulk 엔드포인트에도 동일하게 적용되는지 확인합니다.
    response = client.post("/api/v1/admin/regulation-chunks/bulk", json=build_bulk_request_payload())

    assert response.status_code == 401
    assert response.json() == {
        "status": 401,
        "message": "admin token required",
        "data": None,
        "error_code": "UNAUTHORIZED",
    }


def test_admin_regulation_chunks_api_returns_server_error_when_admin_token_setting_is_missing(
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
