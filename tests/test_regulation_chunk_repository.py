"""regulation_chunk repository가 ORM 모델에 값을 올바르게 매핑하는지 검증하는 테스트 파일입니다."""

from app.repositories.regulation_chunk_repository import create_regulation_chunk
from app.schemas.regulation_chunk import RegulationChunkCreateRequest


class FakeSession:
    """실제 DB 없이 add/flush/refresh에 전달된 ORM 객체만 확인하기 위한 테스트 더블입니다."""

    def __init__(self) -> None:
        self.added = None
        self.flush_called = False
        self.refresh_called = False

    def add(self, value) -> None:
        self.added = value

    def flush(self) -> None:
        self.flush_called = True

    def refresh(self, value) -> None:
        self.refresh_called = True


def test_create_regulation_chunk_maps_document_id_to_model() -> None:
    # 요청 스키마의 document_id가 repository를 거쳐 ORM 모델에 그대로 들어가는지 확인합니다.
    db = FakeSession()
    payload = RegulationChunkCreateRequest(
        document_id="dorm-rule-001",
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

    regulation_chunk = create_regulation_chunk(
        db=db,
        payload=payload,
        chunk_text="제목: 외박 신청\n본문: 외박은 사전에 신청해야 한다.",
        embedding=[0.1] * 1536,
    )

    assert db.added is regulation_chunk
    assert regulation_chunk.document_id == "dorm-rule-001"
    assert regulation_chunk.chunk_id == "dorm-rule-001-03"
    assert db.flush_called is True
    assert db.refresh_called is True
