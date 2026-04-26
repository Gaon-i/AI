"""regulation_chunk 문서 기준 요청 스키마와 에러 계약을 검증하는 테스트 파일입니다."""

import pytest
from pydantic import ValidationError

from app.core import error_codes
from app.schemas.regulation_chunk import RegulationChunkBulkIngestionRequest
from app.schemas.regulation_chunk import RegulationChunkIngestionRequest


def test_regulation_chunk_ingestion_request_accepts_valid_document_id() -> None:
    payload = RegulationChunkIngestionRequest(regulation_document_id=11)

    assert payload.regulation_document_id == 11


def test_regulation_chunk_ingestion_request_rejects_non_positive_document_id() -> None:
    with pytest.raises(ValidationError):
        RegulationChunkIngestionRequest(regulation_document_id=0)


def test_regulation_chunk_bulk_ingestion_request_requires_items() -> None:
    with pytest.raises(ValidationError):
        RegulationChunkBulkIngestionRequest(regulation_document_ids=[])


def test_regulation_chunk_bulk_ingestion_request_limits_items_to_twenty() -> None:
    with pytest.raises(ValidationError):
        RegulationChunkBulkIngestionRequest(regulation_document_ids=list(range(1, 22)))


def test_regulation_chunk_bulk_ingestion_request_accepts_twenty_items() -> None:
    payload = RegulationChunkBulkIngestionRequest(regulation_document_ids=list(range(1, 21)))

    assert len(payload.regulation_document_ids) == 20


def test_regulation_chunk_error_codes_match_expected_contract() -> None:
    assert error_codes.REGULATION_CHUNK_ALREADY_EXISTS.code == "REGULATION_CHUNK_ALREADY_EXISTS"
    assert error_codes.REGULATION_CHUNK_ALREADY_EXISTS.status == 409
    assert error_codes.REGULATION_CHUNK_INGEST_FAILED.code == "REGULATION_CHUNK_INGEST_FAILED"
    assert error_codes.REGULATION_CHUNK_INGEST_FAILED.status == 500
    assert error_codes.REGULATION_DOCUMENT_INGEST_FAILED.code == "REGULATION_DOCUMENT_INGEST_FAILED"
    assert error_codes.REGULATION_DOCUMENT_INGEST_FAILED.status == 500
    assert error_codes.EMBEDDING_GENERATION_FAILED.code == "EMBEDDING_GENERATION_FAILED"
    assert error_codes.EMBEDDING_GENERATION_FAILED.status == 502
    assert error_codes.INVALID_CHUNK_TEXT.code == "INVALID_CHUNK_TEXT"
    assert error_codes.INVALID_CHUNK_TEXT.status == 400
