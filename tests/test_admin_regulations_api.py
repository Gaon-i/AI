"""관리자용 regulation_document CRUD API의 요청/응답 계약을 검증하는 테스트 파일입니다."""

from datetime import datetime

from fastapi.testclient import TestClient

from app.api import admin_regulations as admin_regulations_module
from app.core.error_codes import REGULATION_DOCUMENT_NOT_FOUND
from app.core.exceptions import AppException
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
        source_type="official",
        is_active=True,
        deactivated_at=None,
        is_deleted=False,
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
        "source_type": "official",
    }


def test_create_regulation_document_api_returns_created_response(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        admin_regulations_module,
        "create_regulation_document_with_ingestion",
        lambda *_args, **_kwargs: RegulationDocumentCommandResult(
            document=build_document_summary(),
            triggered_action="document_created",
            ingestion_status="succeeded",
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
    assert response.json()["data"]["ingested_chunk_count"] == 2
    assert response.json()["data"]["deactivated_chunk_count"] == 4


def test_update_regulation_document_api_returns_updated_response(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        admin_regulations_module,
        "update_regulation_document_with_ingestion",
        lambda *_args, **_kwargs: RegulationDocumentCommandResult(
            document=build_document_summary(),
            triggered_action="document_updated",
            ingestion_status="succeeded",
            ingested_chunk_count=3,
            deactivated_chunk_count=2,
        ),
    )

    response = client.patch(
        "/api/v1/admin/regulations/1",
        json={"content": "변경된 본문"},
        headers=build_admin_headers(),
    )

    assert response.status_code == 200
    assert response.json()["data"]["deactivated_chunk_count"] == 2


def test_delete_regulation_document_api_returns_deleted_response(
    client: TestClient,
    monkeypatch,
) -> None:
    deleted_summary = build_document_summary().model_copy(update={"is_deleted": True})
    monkeypatch.setattr(
        admin_regulations_module,
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
    assert response.json()["data"]["document"]["is_deleted"] is True


def test_update_regulation_document_api_returns_common_error_response(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        admin_regulations_module,
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
