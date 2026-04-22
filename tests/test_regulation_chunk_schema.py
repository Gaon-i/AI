"""regulation_chunk 요청 스키마와 관련 에러 계약을 검증하는 테스트 파일입니다."""

import pytest
from pydantic import ValidationError

from app.core import error_codes
from app.schemas.regulation_chunk import RegulationChunkBulkCreateRequest
from app.schemas.regulation_chunk import RegulationChunkCreateRequest
from app.schemas.regulation_chunk import RegulationChunkSourceType


def test_regulation_chunk_create_request_accepts_valid_payload() -> None:
    # 정상적인 관리자 요청 바디가 그대로 스키마에 적재되는지 확인합니다.
    payload = RegulationChunkCreateRequest(
        document_id="dorm-rule-001",
        document_version="2026.04",
        chunk_id="dorm-rule-001-03",
        chunk_index=3,
        category="외박",
        dormitory="본관",
        title="외박 신청",
        content="외박은 사전에 신청해야 한다.",
        keywords=["외박", "신청"],
        source="생활관 규정집 2026",
        source_url="https://example.com/rule",
        source_type="official",
    )

    assert payload.document_id == "dorm-rule-001"
    assert payload.document_version == "2026.04"
    assert payload.chunk_id == "dorm-rule-001-03"
    assert payload.source_type == RegulationChunkSourceType.OFFICIAL
    assert str(payload.source_url) == "https://example.com/rule"


def test_regulation_chunk_create_request_rejects_invalid_source_type() -> None:
    # source_type은 enum 기반이라 허용된 값 외에는 validation 단계에서 막혀야 합니다.
    with pytest.raises(ValidationError):
        RegulationChunkCreateRequest(
            document_id="dorm-rule-001",
            document_version="2026.04",
            chunk_id="dorm-rule-001-03",
            chunk_index=3,
            title="외박 신청",
            content="외박은 사전에 신청해야 한다.",
            source_type="invalid",
        )


def test_regulation_chunk_create_request_rejects_blank_required_text() -> None:
    # 공백만 있는 제목/본문/청크 ID가 들어오면 의미 없는 청크가 저장될 수 있어 방지합니다.
    with pytest.raises(ValidationError):
        RegulationChunkCreateRequest(
            document_id="   ",
            document_version="   ",
            chunk_id="   ",
            chunk_index=3,
            title="외박 신청",
            content="외박은 사전에 신청해야 한다.",
            source_type="official",
        )


def test_regulation_chunk_create_request_normalizes_optional_text_and_keywords() -> None:
    # 선택 필드는 trim 및 정규화해서 이후 service/repository가 단순한 값을 받도록 맞춥니다.
    payload = RegulationChunkCreateRequest(
        document_id="  dorm-rule-001  ",
        document_version="  2026.04  ",
        chunk_id="chunk-1",
        chunk_index=0,
        category="  외박  ",
        dormitory="   ",
        title="  외박 신청  ",
        content="  외박은 사전에 신청해야 한다.  ",
        keywords=[" 외박 ", " ", "신청"],
        source="  생활관 규정집 2026  ",
        source_type="community_tip",
    )

    assert payload.document_id == "dorm-rule-001"
    assert payload.document_version == "2026.04"
    assert payload.category == "외박"
    assert payload.dormitory is None
    assert payload.title == "외박 신청"
    assert payload.content == "외박은 사전에 신청해야 한다."
    assert payload.keywords == ["외박", "신청"]
    assert payload.source == "생활관 규정집 2026"


def test_regulation_chunk_create_request_rejects_invalid_source_url() -> None:
    # source_url은 추후 원문 추적에 쓰이므로 문자열이 아니라 실제 URL 형식을 강제합니다.
    with pytest.raises(ValidationError):
        RegulationChunkCreateRequest(
            document_id="dorm-rule-001",
            document_version="2026.04",
            chunk_id="chunk-1",
            chunk_index=0,
            title="외박 신청",
            content="외박은 사전에 신청해야 한다.",
            source_url="not-a-url",
            source_type="official",
        )


def test_regulation_chunk_bulk_create_request_requires_items() -> None:
    # 벌크 적재 API는 최소 1개 이상의 청크가 있어야 의미가 있으므로 빈 배열을 막습니다.
    with pytest.raises(ValidationError):
        RegulationChunkBulkCreateRequest(items=[])


def test_regulation_chunk_bulk_create_request_limits_items_to_twenty() -> None:
    # 벌크 적재는 최대 20개까지만 허용해 외부 임베딩 API와 서버 부하를 제어합니다.
    with pytest.raises(ValidationError):
        RegulationChunkBulkCreateRequest(
            items=[
                RegulationChunkCreateRequest(
                    document_id=f"dorm-rule-{index}",
                    document_version="2026.04",
                    chunk_id=f"dorm-rule-{index}-01",
                    chunk_index=index,
                    title="외박 신청",
                    content="외박은 사전에 신청해야 한다.",
                    source_type="official",
                )
                for index in range(21)
            ]
        )


def test_regulation_chunk_bulk_create_request_accepts_twenty_items() -> None:
    # 상한선인 20개는 정상 요청으로 받아들여져야 합니다.
    payload = RegulationChunkBulkCreateRequest(
        items=[
            RegulationChunkCreateRequest(
                document_id=f"dorm-rule-{index}",
                document_version="2026.04",
                chunk_id=f"dorm-rule-{index}-01",
                chunk_index=index,
                title="외박 신청",
                content="외박은 사전에 신청해야 한다.",
                source_type="official",
            )
            for index in range(20)
        ]
    )

    assert len(payload.items) == 20


def test_regulation_chunk_error_codes_match_expected_contract() -> None:
    # 프론트/클라이언트가 의존할 핵심 에러 코드 이름과 상태값이 바뀌지 않도록 고정합니다.
    assert error_codes.REGULATION_CHUNK_ALREADY_EXISTS.code == "REGULATION_CHUNK_ALREADY_EXISTS"
    assert error_codes.REGULATION_CHUNK_ALREADY_EXISTS.status == 409
    assert error_codes.EMBEDDING_GENERATION_FAILED.code == "EMBEDDING_GENERATION_FAILED"
    assert error_codes.EMBEDDING_GENERATION_FAILED.status == 502
    assert error_codes.INVALID_CHUNK_TEXT.code == "INVALID_CHUNK_TEXT"
    assert error_codes.INVALID_CHUNK_TEXT.status == 400
