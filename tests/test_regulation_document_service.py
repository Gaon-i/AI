"""regulation_document 서비스의 CRUD 및 자동 적재 흐름을 검증하는 테스트 파일입니다."""

from datetime import datetime

import pytest

from app.core.error_codes import REGULATION_DOCUMENT_ALREADY_EXISTS
from app.core.error_codes import REGULATION_DOCUMENT_NOT_FOUND
from app.core.exceptions import AppException
from app.schemas.regulation_document import RegulationDocumentCreateRequest
from app.schemas.regulation_document import RegulationDocumentUpdateRequest
from app.schemas.regulation_chunk import RegulationChunkSourceType
from app.services import regulation_document_service


class FakeSession:
    def __init__(self) -> None:
        self.commit_called = False
        self.rollback_called = False

    def commit(self) -> None:
        self.commit_called = True

    def rollback(self) -> None:
        self.rollback_called = True

    def refresh(self, _value) -> None:
        return None


def build_create_payload() -> RegulationDocumentCreateRequest:
    return RegulationDocumentCreateRequest(
        document_id="dorm-rule",
        document_version="2026.04",
        category="외박",
        dormitory="본관",
        title="외박 신청",
        content="외박은 통합포털에서 신청합니다.\n승인은 사감실에서 확인합니다.",
        source="생활관 규정집 2026",
        source_url="https://example.com/rules/dorm-rule",
        source_type="official",
    )


def test_create_regulation_document_with_ingestion_returns_success(monkeypatch: pytest.MonkeyPatch) -> None:
    db = FakeSession()
    payload = build_create_payload()

    saved_document = type(
        "SavedDocument",
        (),
        {
            "regulation_document_id": 1,
            "document_id": payload.document_id,
            "document_version": payload.document_version,
            "category": payload.category,
            "dormitory": payload.dormitory,
            "title": payload.title,
            "content": payload.content,
            "source": payload.source,
            "source_url": str(payload.source_url),
            "source_type": payload.source_type.value,
            "is_active": False,
            "deactivated_at": None,
            "is_deleted": False,
            "created_at": datetime(2026, 4, 22, 12, 0, 0),
            "updated_at": datetime(2026, 4, 22, 12, 0, 0),
        },
    )()

    monkeypatch.setattr(
        regulation_document_service,
        "find_regulation_document_by_document_key",
        lambda *_args: None,
    )
    monkeypatch.setattr(
        regulation_document_service,
        "create_regulation_document",
        lambda *_args: saved_document,
    )
    monkeypatch.setattr(
        regulation_document_service,
        "find_active_regulation_documents_by_document_id",
        lambda *_args: [object()],
    )
    monkeypatch.setattr(
        regulation_document_service,
        "_run_ingestion_event",
        lambda *_args, **_kwargs: ("succeeded", 2, 4),
    )

    result = regulation_document_service.create_regulation_document_with_ingestion(db, payload)

    assert result.document.regulation_document_id == 1
    assert result.ingestion_status == "succeeded"
    assert result.ingested_chunk_count == 2
    assert result.deactivated_chunk_count == 4
    assert result.triggered_action == "document_created"


def test_create_regulation_document_with_ingestion_raises_on_duplicate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = FakeSession()
    payload = build_create_payload()

    monkeypatch.setattr(
        regulation_document_service,
        "find_regulation_document_by_document_key",
        lambda *_args: object(),
    )

    with pytest.raises(AppException) as exc_info:
        regulation_document_service.create_regulation_document_with_ingestion(db, payload)

    assert exc_info.value.error_code == REGULATION_DOCUMENT_ALREADY_EXISTS


def test_update_regulation_document_with_ingestion_reingests_when_content_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = FakeSession()
    regulation_document = type(
        "SavedDocument",
        (),
        {
            "regulation_document_id": 1,
            "document_id": "dorm-rule",
            "document_version": "2026.04",
            "category": "외박",
            "dormitory": "본관",
            "title": "외박 신청",
            "content": "기존 본문",
            "source": "생활관 규정집 2026",
            "source_url": "https://example.com/rules/dorm-rule",
            "source_type": "official",
            "is_active": True,
            "deactivated_at": None,
            "is_deleted": False,
            "created_at": datetime(2026, 4, 22, 12, 0, 0),
            "updated_at": datetime(2026, 4, 22, 12, 0, 0),
        },
    )()
    payload = RegulationDocumentUpdateRequest(content="변경된 본문")

    monkeypatch.setattr(
        regulation_document_service,
        "find_regulation_document_by_id",
        lambda *_args: regulation_document,
    )
    monkeypatch.setattr(
        regulation_document_service,
        "update_regulation_document",
        lambda document, update_payload: setattr(document, "content", update_payload.content) or document,
    )
    monkeypatch.setattr(
        regulation_document_service,
        "_run_reingestion_event",
        lambda *_args: ("succeeded", 3, 2),
    )

    result = regulation_document_service.update_regulation_document_with_ingestion(db, 1, payload)

    assert result.ingestion_status == "succeeded"
    assert result.ingested_chunk_count == 3
    assert result.deactivated_chunk_count == 2


def test_delete_regulation_document_marks_deleted_and_deactivates_chunks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = FakeSession()
    regulation_document = type(
        "SavedDocument",
        (),
        {
            "regulation_document_id": 1,
            "document_id": "dorm-rule",
            "document_version": "2026.04",
            "category": "외박",
            "dormitory": "본관",
            "title": "외박 신청",
            "content": "본문",
            "source": "생활관 규정집 2026",
            "source_url": "https://example.com/rules/dorm-rule",
            "source_type": "official",
            "is_active": True,
            "deactivated_at": None,
            "is_deleted": False,
            "deleted_at": None,
            "created_at": datetime(2026, 4, 22, 12, 0, 0),
            "updated_at": datetime(2026, 4, 22, 12, 0, 0),
        },
    )()

    monkeypatch.setattr(
        regulation_document_service,
        "find_regulation_document_by_id",
        lambda *_args: regulation_document,
    )
    monkeypatch.setattr(
        regulation_document_service,
        "deactivate_chunks_for_document",
        lambda *_args: 4,
    )
    monkeypatch.setattr(
        regulation_document_service,
        "mark_regulation_document_deleted",
        lambda document, deleted_at: setattr(document, "is_deleted", True)
        or setattr(document, "deleted_at", deleted_at)
        or document,
    )

    result = regulation_document_service.delete_regulation_document(db, 1)

    assert result.document.is_deleted is True
    assert result.deactivated_chunk_count == 4
    assert result.triggered_action == "document_deleted"


def test_delete_regulation_document_raises_when_document_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = FakeSession()
    monkeypatch.setattr(
        regulation_document_service,
        "find_regulation_document_by_id",
        lambda *_args: None,
    )

    with pytest.raises(AppException) as exc_info:
        regulation_document_service.delete_regulation_document(db, 1)

    assert exc_info.value.error_code == REGULATION_DOCUMENT_NOT_FOUND
