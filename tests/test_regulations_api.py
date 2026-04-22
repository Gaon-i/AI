from fastapi.testclient import TestClient

from app.api import regulations as regulations_module
from app.schemas.regulation_lookup import RegulationDocumentTypeListResult
from app.schemas.regulation_lookup import RegulationDocumentTypeSummary
from app.schemas.regulation_lookup import RegulationLookupDocument
from app.schemas.regulation_lookup import RegulationLookupResult


def test_get_regulation_document_types_api_returns_list(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        regulations_module,
        "get_regulation_document_types",
        lambda *_args, **_kwargs: RegulationDocumentTypeListResult(
            items=[
                RegulationDocumentTypeSummary(document_type="admission", document_count=32),
                RegulationDocumentTypeSummary(document_type="facility", document_count=24),
            ]
        ),
    )

    response = client.get("/api/v1/regulations/document-types")

    assert response.status_code == 200
    assert response.json() == {
        "status": 200,
        "message": "regulation document types retrieved",
        "data": {
            "items": [
                {"document_type": "admission", "document_count": 32},
                {"document_type": "facility", "document_count": 24},
            ]
        },
        "error_code": None,
    }


def test_get_regulation_documents_by_type_api_returns_documents(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        regulations_module,
        "get_regulation_documents_by_type",
        lambda *_args, **_kwargs: RegulationLookupResult(
            document_type="facility",
            total_count=1,
            items=[
                RegulationLookupDocument(
                    regulation_document_id=1,
                    document_id="facility_007",
                    document_version="v1",
                    document_type="facility",
                    category="시설안내",
                    dormitory="제1학생생활관",
                    title="제1학생생활관 학생식당 위치",
                    content="학생식당은 1층에 있습니다.",
                    source="manual",
                    source_url="https://example.com/facility_007",
                    keywords=["식당"],
                    source_type="MARKDOWN",
                    is_active=True,
                    created_at="2026-04-27T10:00:00",
                    updated_at="2026-04-27T10:00:01",
                )
            ],
        ),
    )

    response = client.get("/api/v1/regulations?document_type=facility")

    assert response.status_code == 200
    assert response.json() == {
        "status": 200,
        "message": "regulation documents retrieved",
        "data": {
            "document_type": "facility",
            "total_count": 1,
            "items": [
                {
                    "regulation_document_id": 1,
                    "document_id": "facility_007",
                    "document_version": "v1",
                    "document_type": "facility",
                    "category": "시설안내",
                    "dormitory": "제1학생생활관",
                    "title": "제1학생생활관 학생식당 위치",
                    "content": "학생식당은 1층에 있습니다.",
                    "source": "manual",
                    "source_url": "https://example.com/facility_007",
                    "keywords": ["식당"],
                    "source_type": "MARKDOWN",
                    "is_active": True,
                    "created_at": "2026-04-27T10:00:00",
                    "updated_at": "2026-04-27T10:00:01",
                }
            ],
        },
        "error_code": None,
    }


def test_get_regulation_documents_by_type_api_rejects_blank_query(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/regulations?document_type=   ")

    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"
