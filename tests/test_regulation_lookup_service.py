from datetime import datetime

from app.services import regulation_lookup_service


def test_get_regulation_documents_by_type_returns_mapped_documents(monkeypatch) -> None:
    documents = [
        type(
            "RegulationDocumentStub",
            (),
            {
                "regulation_document_id": 1,
                "document_id": "facility_007",
                "document_version": "v1",
                "category": "시설안내",
                "dormitory": "제1학생생활관",
                "title": "제1학생생활관 학생식당 위치",
                "content": "학생식당은 1층에 있습니다.",
                "source": "manual",
                "source_url": "https://example.com/facility_007",
                "keywords": ["식당"],
                "source_type": "MARKDOWN",
                "is_active": True,
                "created_at": datetime(2026, 4, 27, 10, 0, 0),
                "updated_at": datetime(2026, 4, 27, 10, 0, 1),
            },
        )(),
        type(
            "RegulationDocumentStub",
            (),
            {
                "regulation_document_id": 2,
                "document_id": "facility_008",
                "document_version": "v1",
                "category": "시설안내",
                "dormitory": "제2학생생활관",
                "title": "제2학생생활관 수용현황",
                "content": "총 수용 인원 안내",
                "source": "manual",
                "source_url": "https://example.com/facility_008",
                "keywords": None,
                "source_type": "MARKDOWN",
                "is_active": True,
                "created_at": datetime(2026, 4, 27, 10, 0, 2),
                "updated_at": datetime(2026, 4, 27, 10, 0, 3),
            },
        )(),
    ]
    monkeypatch.setattr(
        regulation_lookup_service,
        "list_active_regulation_documents_by_type",
        lambda *_args, **_kwargs: documents,
    )

    result = regulation_lookup_service.get_regulation_documents_by_type(object(), " facility ")

    assert result.document_type == "facility"
    assert result.total_count == 2
    assert result.items[0].document_id == "facility_007"
    assert result.items[0].document_type == "facility"


def test_get_regulation_document_types_returns_summaries(monkeypatch) -> None:
    monkeypatch.setattr(
        regulation_lookup_service,
        "list_active_regulation_document_types",
        lambda *_args, **_kwargs: [
            {"document_type": "admission", "document_count": 32},
            {"document_type": "facility", "document_count": 24},
            {"document_type": "facility_usage", "document_count": 31},
        ],
    )

    result = regulation_lookup_service.get_regulation_document_types(object())

    assert len(result.items) == 3
    assert result.items[1].document_type == "facility"
    assert result.items[1].document_count == 24
