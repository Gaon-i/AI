"""regulation_chunk repository가 문서 기준 청크 저장을 올바르게 처리하는지 검증합니다."""

from types import SimpleNamespace

from app.repositories import regulation_chunk_repository


class FakeSession:
    """실제 DB 없이 add/flush/refresh에 전달된 ORM 객체만 확인하기 위한 테스트 더블입니다."""

    def __init__(self) -> None:
        self.added: list[object] = []
        self.flush_called = False
        self.refresh_called_values: list[object] = []

    def add(self, value) -> None:
        self.added.append(value)

    def flush(self) -> None:
        self.flush_called = True

    def refresh(self, value) -> None:
        self.refresh_called_values.append(value)


def test_create_regulation_chunks_for_document_maps_document_fields_to_model() -> None:
    db = FakeSession()
    regulation_document = SimpleNamespace(
        regulation_document_id=7,
        document_id="dorm-rule-001",
        document_version="2026.04",
        keywords=["외박", "외출"],
    )
    regulation_chunk_repository.get_settings = lambda: SimpleNamespace(
        openai_embedding_model="text-embedding-3-small"
    )

    created_chunks = regulation_chunk_repository.create_regulation_chunks_for_document(
        db=db,
        regulation_document=regulation_document,
        chunk_texts=["제목: 외박 신청\n본문: 외박은 사전에 신청해야 한다."],
        embeddings=[[0.1] * 1536],
    )

    assert len(created_chunks) == 1
    regulation_chunk = created_chunks[0]
    assert db.added == [regulation_chunk]
    assert regulation_chunk.regulation_document_id == 7
    assert regulation_chunk.document_version == "2026.04"
    assert regulation_chunk.keywords == ["외박", "외출"]
    assert regulation_chunk.embedding_model == "text-embedding-3-small"
    assert db.flush_called is True
    assert db.refresh_called_values == [regulation_chunk]


def test_count_chunks_for_document_uses_count_query() -> None:
    executed_statements: list[object] = []

    class CountSession:
        def execute(self, statement):
            executed_statements.append(statement)
            return SimpleNamespace(scalar=lambda: 3)

    result = regulation_chunk_repository.count_chunks_for_document(CountSession(), 7)

    assert result == 3
    assert len(executed_statements) == 1
