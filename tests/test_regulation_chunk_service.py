"""regulation_chunk 생성 서비스의 비즈니스 흐름을 검증하는 테스트 파일입니다."""

import pytest

from app.core.error_codes import REGULATION_CHUNK_ALREADY_EXISTS
from app.core.error_codes import REGULATION_CHUNK_BULK_CREATE_FAILED
from app.core.error_codes import REGULATION_CHUNK_CREATE_FAILED
from app.core.exceptions import AppException
from app.schemas.regulation_chunk import RegulationChunkBulkCreateRequest
from app.schemas.regulation_chunk import RegulationChunkCreateRequest
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


def build_payload() -> RegulationChunkCreateRequest:
    # 여러 테스트에서 공통으로 쓰는 정상 요청 바디를 한 곳에서 만듭니다.
    return RegulationChunkCreateRequest(
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


def build_bulk_payload(count: int = 2) -> RegulationChunkBulkCreateRequest:
    # 벌크 테스트에서 여러 청크를 빠르게 만들기 위한 공통 요청 바디입니다.
    return RegulationChunkBulkCreateRequest(
        items=[
            RegulationChunkCreateRequest(
                document_id="dorm-rule-001",
                document_version="2026.04",
                chunk_id=f"dorm-rule-001-{index:02d}",
                chunk_index=index,
                category="외박",
                dormitory="본관",
                title=f"외박 신청 {index}",
                content="외박은 사전에 신청해야 한다.",
                keywords=["외박", "신청"],
                source="생활관 규정집 2026",
                source_url="https://example.com/rule",
                source_type="official",
            )
            for index in range(1, count + 1)
        ]
    )


def test_build_chunk_text_includes_expected_fields() -> None:
    # 임베딩 품질에 직접 영향을 주는 chunk_text 포맷이 누락 없이 조합되는지 확인합니다.
    chunk_text = regulation_chunk_service.build_chunk_text(build_payload())

    assert "생활관: 본관" in chunk_text
    assert "카테고리: 외박" in chunk_text
    assert "제목: 외박 신청" in chunk_text
    assert "본문: 외박은 사전에 신청해야 한다." in chunk_text
    assert "키워드: 외박, 신청" in chunk_text
    assert "출처: 생활관 규정집 2026" in chunk_text
    assert "출처 URL: https://example.com/rule" in chunk_text
    assert "출처유형: official" in chunk_text


def test_create_regulation_chunk_with_embedding_returns_result(monkeypatch: pytest.MonkeyPatch) -> None:
    # 서비스의 정상 흐름을 테스트하기 위해 DB 저장과 임베딩 생성을 monkeypatch로 대체합니다.
    payload = build_payload()
    db = FakeSession()

    monkeypatch.setattr(regulation_chunk_service, "find_by_chunk_id", lambda *_: None)
    monkeypatch.setattr(regulation_chunk_service, "create_embedding", lambda _: [0.1] * 1536)

    class SavedChunk:
        # repository가 저장 후 반환했다고 가정하는 최소 모델 형태입니다.
        regulation_chunk_id = 1
        regulation_document_id = 11
        chunk_id = payload.chunk_id
        chunk_index = payload.chunk_index

    def fake_create_regulation_chunk(**kwargs):
        # service가 repository로 넘기는 데이터가 기대한 값인지 함께 검증합니다.
        assert kwargs["payload"] == payload
        assert "제목: 외박 신청" in kwargs["chunk_text"]
        assert len(kwargs["embedding"]) == 1536
        return SavedChunk()

    monkeypatch.setattr(
        regulation_chunk_service,
        "create_regulation_chunk",
        fake_create_regulation_chunk,
    )

    result = regulation_chunk_service.create_regulation_chunk_with_embedding(db, payload)

    assert result.regulation_chunk_id == 1
    assert result.regulation_document_id == 11
    assert result.document_id == payload.document_id
    assert result.document_version == payload.document_version
    assert result.chunk_id == payload.chunk_id
    assert result.chunk_index == payload.chunk_index
    assert result.source_type == payload.source_type
    assert db.commit_called is True
    assert db.rollback_called is False


def test_create_regulation_chunk_with_embedding_raises_when_chunk_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 중복 chunk_id는 외부 API 호출이나 저장 전에 바로 차단돼야 합니다.
    payload = build_payload()
    db = FakeSession()

    monkeypatch.setattr(regulation_chunk_service, "find_by_chunk_id", lambda *_: object())

    with pytest.raises(AppException) as exc_info:
        regulation_chunk_service.create_regulation_chunk_with_embedding(db, payload)

    assert exc_info.value.error_code == REGULATION_CHUNK_ALREADY_EXISTS
    assert db.commit_called is False
    assert db.rollback_called is True


def test_create_regulation_chunk_with_embedding_rolls_back_on_repository_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 저장 단계 예외는 rollback 후 공통 도메인 에러로 변환돼야 합니다.
    payload = build_payload()
    db = FakeSession()

    monkeypatch.setattr(regulation_chunk_service, "find_by_chunk_id", lambda *_: None)
    monkeypatch.setattr(regulation_chunk_service, "create_embedding", lambda _: [0.1] * 1536)
    monkeypatch.setattr(
        regulation_chunk_service,
        "create_regulation_chunk",
        lambda **_: (_ for _ in ()).throw(RuntimeError("insert failed")),
    )

    with pytest.raises(AppException) as exc_info:
        regulation_chunk_service.create_regulation_chunk_with_embedding(db, payload)

    assert exc_info.value.error_code == REGULATION_CHUNK_CREATE_FAILED
    assert db.commit_called is False
    assert db.rollback_called is True


def test_create_regulation_chunks_with_embeddings_returns_bulk_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 벌크 성공 시 생성 건수와 각 항목 상태가 응답용 결과로 정리돼야 합니다.
    payload = build_bulk_payload()
    db = FakeSession()
    captured_chunk_texts = []

    class SavedChunk:
        def __init__(self, chunk_id: str) -> None:
            self.chunk_id = chunk_id

    monkeypatch.setattr(
        regulation_chunk_service,
        "find_existing_chunk_ids",
        lambda _db, _chunk_ids: set(),
    )
    monkeypatch.setattr(
        regulation_chunk_service,
        "create_embeddings_batch",
        lambda chunk_texts: [[0.1] * 1536 for _ in chunk_texts],
    )

    def fake_create_regulation_chunk(**kwargs):
        captured_chunk_texts.append(kwargs["chunk_text"])
        return SavedChunk(kwargs["payload"].chunk_id)

    monkeypatch.setattr(
        regulation_chunk_service,
        "create_regulation_chunk",
        fake_create_regulation_chunk,
    )

    result = regulation_chunk_service.create_regulation_chunks_with_embeddings(db, payload)

    assert result.created_count == 2
    assert [item.model_dump() for item in result.items] == [
        {"chunk_id": "dorm-rule-001-01", "status": "created"},
        {"chunk_id": "dorm-rule-001-02", "status": "created"},
    ]
    assert len(captured_chunk_texts) == 2
    assert db.commit_called is True
    assert db.rollback_called is False


def test_create_regulation_chunks_with_embeddings_rolls_back_when_one_item_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 벌크 적재 정책은 전체 실패이므로 중간 항목 하나라도 실패하면 전체 rollback 해야 합니다.
    payload = build_bulk_payload()
    db = FakeSession()
    persisted_chunk_ids = set()

    monkeypatch.setattr(
        regulation_chunk_service,
        "find_existing_chunk_ids",
        lambda _db, _chunk_ids: set(),
    )
    monkeypatch.setattr(
        regulation_chunk_service,
        "create_embeddings_batch",
        lambda chunk_texts: [[0.1] * 1536 for _ in chunk_texts],
    )

    def fake_create_regulation_chunk(**kwargs):
        persisted_chunk_ids.add(kwargs["payload"].chunk_id)
        if kwargs["payload"].chunk_id == "dorm-rule-001-02":
            raise AppException(REGULATION_CHUNK_ALREADY_EXISTS)
        return type("SavedChunk", (), {"chunk_id": kwargs["payload"].chunk_id})()

    monkeypatch.setattr(
        regulation_chunk_service,
        "create_regulation_chunk",
        fake_create_regulation_chunk,
    )

    with pytest.raises(AppException) as exc_info:
        regulation_chunk_service.create_regulation_chunks_with_embeddings(db, payload)

    assert exc_info.value.error_code == REGULATION_CHUNK_ALREADY_EXISTS
    assert persisted_chunk_ids == {"dorm-rule-001-01", "dorm-rule-001-02"}
    assert db.commit_called is False
    assert db.rollback_called is True


def test_create_regulation_chunks_with_embeddings_wraps_unexpected_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 예상치 못한 런타임 예외는 벌크 생성 실패 코드로 한 번 감싸서 반환합니다.
    payload = build_bulk_payload()
    db = FakeSession()

    monkeypatch.setattr(
        regulation_chunk_service,
        "find_existing_chunk_ids",
        lambda _db, _chunk_ids: set(),
    )
    monkeypatch.setattr(
        regulation_chunk_service,
        "create_embeddings_batch",
        lambda chunk_texts: [[0.1] * 1536 for _ in chunk_texts],
    )

    monkeypatch.setattr(
        regulation_chunk_service,
        "create_regulation_chunk",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("unexpected failure")),
    )

    with pytest.raises(AppException) as exc_info:
        regulation_chunk_service.create_regulation_chunks_with_embeddings(db, payload)

    assert exc_info.value.error_code == REGULATION_CHUNK_BULK_CREATE_FAILED
    assert db.commit_called is False
    assert db.rollback_called is True


def test_create_regulation_chunks_with_embeddings_rejects_duplicate_chunk_id_in_same_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 같은 요청 안에 동일한 chunk_id가 있으면 전체 실패 정책에 따라 rollback 해야 합니다.
    payload = RegulationChunkBulkCreateRequest(
        items=[
            build_payload(),
            build_payload(),
        ]
    )
    db = FakeSession()
    with pytest.raises(AppException) as exc_info:
        regulation_chunk_service.create_regulation_chunks_with_embeddings(db, payload)

    assert exc_info.value.error_code == REGULATION_CHUNK_ALREADY_EXISTS
    assert db.commit_called is False
    assert db.rollback_called is True
