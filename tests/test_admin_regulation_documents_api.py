"""관리자용 regulation_document CRUD 및 rechunk API의 요청/응답 계약을 검증하는 테스트 파일입니다."""

from datetime import datetime

from fastapi.testclient import TestClient

from app.api import admin_regulation_documents as admin_regulation_documents_module
from app.core.error_codes import REGULATION_DOCUMENT_NOT_FOUND
from app.core.exceptions import AppException
from app.schemas.regulation_document import RegulationDocumentBulkCreateResult
from app.schemas.regulation_document import RegulationDocumentCommandResult
from app.schemas.regulation_document import RegulationDocumentSummary


def build_admin_headers(token: str = "test-admin-token") -> dict[str, str]:
    return {"X-Admin-Token": token}


def build_document_summary() -> RegulationDocumentSummary:
    return RegulationDocumentSummary(
        regulation_document_id=1,
        document_id="dorm-rule",
        document_version="2026.04",
        category="외박",
        dormitory="본관",
        title="외박 신청",
        content="외박은 통합포털에서 신청합니다.",
        source="생활관 규정집 2026",
        source_url="https://example.com/rules/dorm-rule",
        keywords=["외박", "외출", "통합포털"],
        source_type="official",
        is_active=True,
        created_at=datetime(2026, 4, 22, 12, 0, 0),
        updated_at=datetime(2026, 4, 22, 12, 0, 0),
    )


def build_create_payload() -> dict:
    return {
        "document_id": "dorm-rule",
        "document_version": "2026.04",
        "category": "외박",
        "dormitory": "본관",
        "title": "외박 신청",
        "content": "외박은 통합포털에서 신청합니다.",
        "source": "생활관 규정집 2026",
        "source_url": "https://example.com/rules/dorm-rule",
        "keywords": ["외박", "외출", "통합포털"],
        "source_type": "official",
    }


def build_bulk_create_payload(count: int = 2) -> dict:
    return {
        "items": [
            {
                "document_id": f"dorm-rule-{index}",
                "document_version": f"2026.{index:02d}",
                "category": "외박",
                "dormitory": "본관",
                "title": f"외박 신청 {index}",
                "content": "외박은 통합포털에서 신청합니다.",
                "source": "생활관 규정집 2026",
                "source_url": "https://example.com/rules/dorm-rule",
                "keywords": ["외박", "외출", "통합포털"],
                "source_type": "official",
            }
            for index in range(1, count + 1)
        ]
    }


def test_create_regulation_document_api_returns_created_response(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        admin_regulation_documents_module,
        "create_regulation_document_with_ingestion",
        lambda *_args, **_kwargs: RegulationDocumentCommandResult(
            document=build_document_summary(),
            triggered_action="document_created",
            ingestion_status="succeeded",
            ingestion_error_code=None,
            ingested_chunk_count=2,
            deactivated_chunk_count=4,
        ),
    )

    response = client.post(
        "/api/v1/admin/regulations",
        json=build_create_payload(),
        headers=build_admin_headers(),
    )

    assert response.status_code == 201
    assert response.json()["data"]["triggered_action"] == "document_created"
    assert response.json()["data"]["ingestion_error_code"] is None
    assert response.json()["data"]["ingested_chunk_count"] == 2
    assert response.json()["data"]["deactivated_chunk_count"] == 4


def test_create_regulation_documents_bulk_api_returns_created_response(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        admin_regulation_documents_module,
        "create_regulation_documents_with_ingestion",
        lambda *_args, **_kwargs: RegulationDocumentBulkCreateResult(
            total_count=2,
            created_count=1,
            failed_count=1,
            items=[
                {
                    "status": "created",
                    "document_id": "dorm-rule-1",
                    "document_version": "2026.01",
                    "result": {
                        "document": build_document_summary().model_dump(),
                        "triggered_action": "document_created",
                        "ingestion_status": "succeeded",
                        "ingestion_error_code": None,
                        "ingested_chunk_count": 2,
                        "deactivated_chunk_count": 0,
                    },
                    "error_code": None,
                    "message": None,
                },
                {
                    "status": "failed",
                    "document_id": "dorm-rule-2",
                    "document_version": "2026.02",
                    "result": None,
                    "error_code": "REGULATION_DOCUMENT_ALREADY_EXISTS",
                    "message": "regulation document already exists",
                },
            ],
        ),
    )

    response = client.post(
        "/api/v1/admin/regulations/bulk",
        json=build_bulk_create_payload(),
        headers=build_admin_headers(),
    )

    assert response.status_code == 201
    assert response.json()["data"]["total_count"] == 2
    assert response.json()["data"]["created_count"] == 1
    assert response.json()["data"]["failed_count"] == 1
    assert response.json()["data"]["items"][1]["error_code"] == "REGULATION_DOCUMENT_ALREADY_EXISTS"


def test_update_regulation_document_api_returns_updated_response(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        admin_regulation_documents_module,
        "update_regulation_document_with_ingestion",
        lambda *_args, **_kwargs: RegulationDocumentCommandResult(
            document=build_document_summary(),
            triggered_action="document_updated",
            ingestion_status="failed",
            ingestion_error_code="OPENAI_API_TIMEOUT",
            ingested_chunk_count=0,
            deactivated_chunk_count=2,
        ),
    )

    response = client.patch(
        "/api/v1/admin/regulations/1",
        json={"content": "변경된 본문"},
        headers=build_admin_headers(),
    )

    assert response.status_code == 200
    assert response.json()["data"]["ingestion_error_code"] == "OPENAI_API_TIMEOUT"
    assert response.json()["data"]["deactivated_chunk_count"] == 2


def test_delete_regulation_document_api_returns_deleted_response(
    client: TestClient,
    monkeypatch,
) -> None:
    deleted_summary = build_document_summary().model_copy(update={"is_active": False})
    monkeypatch.setattr(
        admin_regulation_documents_module,
        "delete_regulation_document",
        lambda *_args, **_kwargs: RegulationDocumentCommandResult(
            document=deleted_summary,
            triggered_action="document_deleted",
            deactivated_chunk_count=4,
        ),
    )

    response = client.delete(
        "/api/v1/admin/regulations/1",
        headers=build_admin_headers(),
    )

    assert response.status_code == 200
    assert response.json()["data"]["document"]["is_active"] is False


def test_rechunk_regulation_document_api_returns_updated_response(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        admin_regulation_documents_module,
        "rechunk_regulation_document",
        lambda *_args, **_kwargs: RegulationDocumentCommandResult(
            document=build_document_summary(),
            triggered_action="document_rechunked",
            ingestion_status="succeeded",
            ingestion_error_code=None,
            ingested_chunk_count=3,
            deactivated_chunk_count=2,
        ),
    )

    response = client.post(
        "/api/v1/admin/regulations/1/rechunk",
        headers=build_admin_headers(),
    )

    assert response.status_code == 200
    assert response.json()["data"]["triggered_action"] == "document_rechunked"
    assert response.json()["data"]["ingested_chunk_count"] == 3
    assert response.json()["data"]["deactivated_chunk_count"] == 2


def test_create_regulation_documents_bulk_api_rejects_more_than_twenty_items(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/admin/regulations/bulk",
        json=build_bulk_create_payload(count=21),
        headers=build_admin_headers(),
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"


def test_update_regulation_document_api_returns_common_error_response(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        admin_regulation_documents_module,
        "update_regulation_document_with_ingestion",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AppException(REGULATION_DOCUMENT_NOT_FOUND)),
    )

    response = client.patch(
        "/api/v1/admin/regulations/999",
        json={"content": "변경된 본문"},
        headers=build_admin_headers(),
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "REGULATION_DOCUMENT_NOT_FOUND"


def test_rechunk_regulation_document_api_returns_common_error_response(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        admin_regulation_documents_module,
        "rechunk_regulation_document",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AppException(REGULATION_DOCUMENT_NOT_FOUND)),
    )

    response = client.post(
        "/api/v1/admin/regulations/999/rechunk",
        headers=build_admin_headers(),
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "REGULATION_DOCUMENT_NOT_FOUND"
