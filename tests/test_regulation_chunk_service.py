"""regulation_chunk 문서 기준 적재 서비스의 비즈니스 흐름을 검증합니다."""

import pytest

from app.core.error_codes import REGULATION_CHUNK_ALREADY_EXISTS
from app.core.error_codes import REGULATION_CHUNK_INGEST_FAILED
from app.core.error_codes import REGULATION_DOCUMENT_NOT_FOUND
from app.core.exceptions import AppException
from app.schemas.regulation_chunk import RegulationChunkBulkIngestionRequest
from app.schemas.regulation_chunk import RegulationChunkIngestionRequest
from app.services import regulation_chunk_service


class FakeSession:
    """DB 세션 전체를 쓰지 않고 commit/rollback 호출 여부만 확인하기 위한 테스트 더블입니다."""

    def __init__(self) -> None:
        self.commit_called = False
        self.rollback_called = False

    def commit(self) -> None:
        self.commit_called = True

    def rollback(self) -> None:
        self.rollback_called = True


def test_ingest_regulation_chunks_for_document_returns_created_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = FakeSession()
    regulation_document = type(
        "RegulationDocumentStub",
        (),
        {
            "regulation_document_id": 11,
            "document_id": "dorm-rule-001",
            "document_version": "2026.04",
            "title": "외박 신청",
            "content": "외박은 사전에 신청해야 한다.",
            "category": "외박",
            "dormitory": "본관",
            "source": "생활관 규정집 2026",
            "source_url": "https://example.com/rule",
            "source_type": "official",
        },
    )()

    monkeypatch.setattr(
        regulation_chunk_service,
        "find_regulation_document_by_id",
        lambda *_args: regulation_document,
    )
    monkeypatch.setattr(regulation_chunk_service, "count_chunks_for_document", lambda *_args: 0)
    monkeypatch.setattr(
        regulation_chunk_service,
        "_chunk_document_content",
        lambda *_args: ["chunk 1", "chunk 2"],
    )
    monkeypatch.setattr(
        regulation_chunk_service,
        "create_embeddings_batch",
        lambda chunk_texts: [[0.1] * 1536 for _ in chunk_texts],
    )
    monkeypatch.setattr(
        regulation_chunk_service,
        "create_regulation_chunks_for_document",
        lambda *_args, **_kwargs: [object(), object()],
    )

    result = regulation_chunk_service.ingest_regulation_chunks_for_document(
        db,
        RegulationChunkIngestionRequest(regulation_document_id=11),
    )

    assert result.regulation_document_id == 11
    assert result.document_id == "dorm-rule-001"
    assert result.document_version == "2026.04"
    assert result.created_count == 2
    assert db.commit_called is True
    assert db.rollback_called is False


def test_ingest_regulation_chunks_for_document_raises_when_document_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = FakeSession()

    monkeypatch.setattr(
        regulation_chunk_service,
        "find_regulation_document_by_id",
        lambda *_args: None,
    )

    with pytest.raises(AppException) as exc_info:
        regulation_chunk_service.ingest_regulation_chunks_for_document(
            db,
            RegulationChunkIngestionRequest(regulation_document_id=999),
        )

    assert exc_info.value.error_code == REGULATION_DOCUMENT_NOT_FOUND
    assert db.commit_called is False
    assert db.rollback_called is True


def test_ingest_regulation_chunks_for_document_raises_when_chunks_exist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = FakeSession()
    regulation_document = type(
        "RegulationDocumentStub",
        (),
        {
            "regulation_document_id": 11,
            "document_id": "dorm-rule-001",
            "document_version": "2026.04",
        },
    )()

    monkeypatch.setattr(
        regulation_chunk_service,
        "find_regulation_document_by_id",
        lambda *_args: regulation_document,
    )
    monkeypatch.setattr(regulation_chunk_service, "count_chunks_for_document", lambda *_args: 1)

    with pytest.raises(AppException) as exc_info:
        regulation_chunk_service.ingest_regulation_chunks_for_document(
            db,
            RegulationChunkIngestionRequest(regulation_document_id=11),
        )

    assert exc_info.value.error_code == REGULATION_CHUNK_ALREADY_EXISTS
    assert db.commit_called is False
    assert db.rollback_called is True


def test_ingest_regulation_chunks_for_document_wraps_unexpected_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = FakeSession()
    regulation_document = type(
        "RegulationDocumentStub",
        (),
        {
            "regulation_document_id": 11,
            "document_id": "dorm-rule-001",
            "document_version": "2026.04",
        },
    )()

    monkeypatch.setattr(
        regulation_chunk_service,
        "find_regulation_document_by_id",
        lambda *_args: regulation_document,
    )
    monkeypatch.setattr(regulation_chunk_service, "count_chunks_for_document", lambda *_args: 0)
    monkeypatch.setattr(
        regulation_chunk_service,
        "_chunk_document_content",
        lambda *_args: ["chunk 1"],
    )
    monkeypatch.setattr(
        regulation_chunk_service,
        "create_embeddings_batch",
        lambda _chunk_texts: (_ for _ in ()).throw(RuntimeError("embedding failed")),
    )

    with pytest.raises(AppException) as exc_info:
        regulation_chunk_service.ingest_regulation_chunks_for_document(
            db,
            RegulationChunkIngestionRequest(regulation_document_id=11),
        )

    assert exc_info.value.error_code == REGULATION_CHUNK_INGEST_FAILED
    assert db.commit_called is False
    assert db.rollback_called is True


def test_ingest_regulation_chunks_for_documents_returns_bulk_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = FakeSession()

    monkeypatch.setattr(
        regulation_chunk_service,
        "ingest_regulation_chunks_for_document",
        lambda _db, payload: type(
            "IngestionResultStub",
            (),
            {
                "regulation_document_id": payload.regulation_document_id,
                "created_count": 2,
            },
        )(),
    )

    result = regulation_chunk_service.ingest_regulation_chunks_for_documents(
        db,
        RegulationChunkBulkIngestionRequest(regulation_document_ids=[11, 12]),
    )

    assert result.created_document_count == 2
    assert [item.model_dump() for item in result.items] == [
        {"regulation_document_id": 11, "created_count": 2, "status": "created"},
        {"regulation_document_id": 12, "created_count": 2, "status": "created"},
    ]
