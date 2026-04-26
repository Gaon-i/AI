"""regulation_document 서비스의 CRUD 및 자동 적재 흐름을 검증하는 테스트 파일입니다."""

from datetime import datetime

import pytest

from app.core.error_codes import REGULATION_DOCUMENT_ALREADY_EXISTS
from app.core.error_codes import REGULATION_DOCUMENT_INGEST_FAILED
from app.core.error_codes import REGULATION_DOCUMENT_NOT_FOUND
from app.core.error_codes import OPENAI_API_TIMEOUT
from app.core.exceptions import AppException
from app.schemas.regulation_document import RegulationDocumentBulkCreateRequest
from app.schemas.regulation_document import RegulationDocumentCommandResult
from app.schemas.regulation_document import RegulationDocumentSummary
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
        keywords=["외박", "외출", "통합포털"],
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
            "keywords": payload.keywords,
            "source_type": payload.source_type.value,
            "is_active": False,
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
        lambda *_args, **_kwargs: ("succeeded", None, 2, 4),
    )

    result = regulation_document_service.create_regulation_document_with_ingestion(db, payload)

    assert result.document.regulation_document_id == 1
    assert result.ingestion_status == "succeeded"
    assert result.ingestion_error_code is None
    assert result.ingested_chunk_count == 2
    assert result.deactivated_chunk_count == 4
    assert result.triggered_action == "document_created"


def test_chunk_document_content_returns_standard_chunk_when_content_is_blank(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        regulation_document_service,
        "get_settings",
        lambda: type("SettingsStub", (), {"regulation_chunk_max_length": 800})(),
    )
    regulation_document = type(
        "RegulationDocumentStub",
        (),
        {
            "content": "",
            "title": "외박 신청",
            "dormitory": "제1학생생활관",
            "category": "입퇴사 안내",
            "keywords": ["외박"],
            "source": "생활관 안내",
            "source_url": "https://example.com/rules",
            "source_type": "official",
        },
    )()

    chunks = regulation_document_service._chunk_document_content(regulation_document)

    assert len(chunks) == 1
    assert "제목: 외박 신청" in chunks[0]
    assert "본문:" in chunks[0]


def test_chunk_document_content_splits_long_paragraphs_by_max_length(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        regulation_document_service,
        "get_settings",
        lambda: type("SettingsStub", (), {"regulation_chunk_max_length": 20})(),
    )
    regulation_document = type(
        "RegulationDocumentStub",
        (),
        {
            "content": "가나다라마바사아자차카타파하 가나다라마바사아자차카타파하",
            "title": "긴 문단 테스트",
            "dormitory": None,
            "category": None,
            "keywords": None,
            "source": None,
            "source_url": None,
            "source_type": None,
        },
    )()

    chunks = regulation_document_service._chunk_document_content(regulation_document)

    assert len(chunks) >= 2
    assert all("본문:" in chunk for chunk in chunks)


def test_create_regulation_documents_with_ingestion_returns_partial_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = FakeSession()
    first_payload = build_create_payload()
    second_payload = build_create_payload().model_copy(
        update={"document_id": "dorm-rule-2", "document_version": "2026.05"}
    )

    monkeypatch.setattr(
        regulation_document_service,
        "create_regulation_document_with_ingestion",
        lambda _db, payload: (
            RegulationDocumentCommandResult(
                document=RegulationDocumentSummary(
                    regulation_document_id=1,
                    document_id=payload.document_id,
                    document_version=payload.document_version,
                    category=payload.category,
                    dormitory=payload.dormitory,
                    title=payload.title,
                    content=payload.content,
                    source=payload.source,
                    source_url=str(payload.source_url),
                    keywords=payload.keywords,
                    source_type=payload.source_type.value,
                    is_active=True,
                    created_at=datetime(2026, 4, 22, 12, 0, 0),
                    updated_at=datetime(2026, 4, 22, 12, 0, 0),
                ),
                triggered_action="document_created",
                ingestion_status="succeeded",
                ingestion_error_code=None,
                ingested_chunk_count=2,
                deactivated_chunk_count=0,
            )
            if payload.document_id == "dorm-rule"
            else (_ for _ in ()).throw(AppException(REGULATION_DOCUMENT_ALREADY_EXISTS))
        ),
    )

    result = regulation_document_service.create_regulation_documents_with_ingestion(
        db,
        RegulationDocumentBulkCreateRequest(items=[first_payload, second_payload]),
    )

    assert result.total_count == 2
    assert result.created_count == 1
    assert result.failed_count == 1
    assert result.items[0].status == "created"
    assert result.items[0].result is not None
    assert result.items[1].status == "failed"
    assert result.items[1].error_code == "REGULATION_DOCUMENT_ALREADY_EXISTS"


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
            "keywords": ["외박", "외출"],
            "source_type": "official",
            "is_active": True,
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
        lambda *_args: ("succeeded", None, 3, 2),
    )

    result = regulation_document_service.update_regulation_document_with_ingestion(db, 1, payload)

    assert result.ingestion_status == "succeeded"
    assert result.ingestion_error_code is None
    assert result.ingested_chunk_count == 3
    assert result.deactivated_chunk_count == 2


def test_update_regulation_document_with_ingestion_reingests_when_keywords_change(
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
            "keywords": ["외박"],
            "source_type": "official",
            "is_active": True,
            "created_at": datetime(2026, 4, 22, 12, 0, 0),
            "updated_at": datetime(2026, 4, 22, 12, 0, 0),
        },
    )()
    payload = RegulationDocumentUpdateRequest(keywords=["외박", "외출"])

    monkeypatch.setattr(
        regulation_document_service,
        "find_regulation_document_by_id",
        lambda *_args: regulation_document,
    )
    monkeypatch.setattr(
        regulation_document_service,
        "update_regulation_document",
        lambda document, update_payload: setattr(document, "keywords", update_payload.keywords) or document,
    )
    monkeypatch.setattr(
        regulation_document_service,
        "_run_reingestion_event",
        lambda *_args: ("succeeded", None, 2, 1),
    )

    result = regulation_document_service.update_regulation_document_with_ingestion(db, 1, payload)

    assert result.ingestion_status == "succeeded"
    assert result.ingestion_error_code is None
    assert result.ingested_chunk_count == 2
    assert result.deactivated_chunk_count == 1


def test_rechunk_regulation_document_recreates_chunks(
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
            "keywords": ["외박", "외출"],
            "source_type": "official",
            "is_active": True,
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
        "_run_reingestion_event",
        lambda *_args: ("succeeded", None, 3, 2),
    )

    result = regulation_document_service.rechunk_regulation_document(db, 1)

    assert result.triggered_action == "document_rechunked"
    assert result.ingestion_status == "succeeded"
    assert result.ingestion_error_code is None
    assert result.ingested_chunk_count == 3
    assert result.deactivated_chunk_count == 2


def test_build_chunk_text_includes_keywords() -> None:
    regulation_document = type(
        "SavedDocument",
        (),
        {
            "dormitory": "본관",
            "category": "외박",
            "title": "외박 신청",
            "keywords": ["외박", "외출", "통합포털"],
            "source": "생활관 규정집 2026",
            "source_url": "https://example.com/rules/dorm-rule",
            "source_type": "official",
        },
    )()

    chunk_text = regulation_document_service._build_chunk_text(
        regulation_document,
        "외박은 통합포털에서 신청합니다.",
    )

    assert "키워드: 외박, 외출, 통합포털" in chunk_text


def test_rechunk_regulation_document_raises_when_document_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = FakeSession()

    monkeypatch.setattr(
        regulation_document_service,
        "find_regulation_document_by_id",
        lambda *_args: None,
    )

    with pytest.raises(AppException) as exc_info:
        regulation_document_service.rechunk_regulation_document(db, 1)

    assert exc_info.value.error_code == REGULATION_DOCUMENT_NOT_FOUND


def test_create_regulation_document_with_ingestion_returns_ingestion_error_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
            "keywords": payload.keywords,
            "source_type": payload.source_type.value,
            "is_active": False,
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
        lambda *_args: [],
    )
    monkeypatch.setattr(
        regulation_document_service,
        "_run_ingestion_event",
        lambda *_args, **_kwargs: ("failed", OPENAI_API_TIMEOUT.code, 0, 0),
    )

    result = regulation_document_service.create_regulation_document_with_ingestion(db, payload)

    assert result.ingestion_status == "failed"
    assert result.ingestion_error_code == "OPENAI_API_TIMEOUT"


def test_run_ingestion_event_returns_default_error_code_on_unexpected_failure(
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
            "title": "외박 신청",
            "content": "본문",
            "category": "외박",
            "dormitory": "본관",
            "source": "생활관 규정집 2026",
            "source_url": "https://example.com/rules/dorm-rule",
            "keywords": ["외박", "외출"],
            "source_type": "official",
            "is_active": False,
        },
    )()

    monkeypatch.setattr(
        regulation_document_service,
        "_chunk_document_content",
        lambda *_args: ["chunk 1"],
    )
    monkeypatch.setattr(
        regulation_document_service,
        "create_embeddings_batch",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("embedding failed")),
    )

    status, error_code, ingested_chunk_count, deactivated_chunk_count = (
        regulation_document_service._run_ingestion_event(db, regulation_document, previous_active_documents=[])
    )

    assert status == "failed"
    assert error_code == REGULATION_DOCUMENT_INGEST_FAILED.code
    assert ingested_chunk_count == 0
    assert deactivated_chunk_count == 0


def test_run_ingestion_event_returns_app_error_code_on_domain_failure(
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
            "title": "외박 신청",
            "content": "본문",
            "category": "외박",
            "dormitory": "본관",
            "source": "생활관 규정집 2026",
            "source_url": "https://example.com/rules/dorm-rule",
            "keywords": ["외박", "외출"],
            "source_type": "official",
            "is_active": False,
        },
    )()

    monkeypatch.setattr(
        regulation_document_service,
        "_chunk_document_content",
        lambda *_args: ["chunk 1"],
    )
    monkeypatch.setattr(
        regulation_document_service,
        "create_embeddings_batch",
        lambda *_args: (_ for _ in ()).throw(AppException(OPENAI_API_TIMEOUT)),
    )

    status, error_code, ingested_chunk_count, deactivated_chunk_count = (
        regulation_document_service._run_ingestion_event(db, regulation_document, previous_active_documents=[])
    )

    assert status == "failed"
    assert error_code == OPENAI_API_TIMEOUT.code
    assert ingested_chunk_count == 0
    assert deactivated_chunk_count == 0


def test_delete_regulation_document_deactivates_document_and_chunks(
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
            "keywords": ["외박", "외출"],
            "source_type": "official",
            "is_active": True,
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
        "deactivate_regulation_document",
        lambda document: setattr(document, "is_active", False) or document,
    )

    result = regulation_document_service.delete_regulation_document(db, 1)

    assert result.document.is_active is False
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
