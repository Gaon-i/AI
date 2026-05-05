"""regulation_chunk repository가 문서 기준 청크 저장을 올바르게 처리하는지 검증합니다."""

from types import SimpleNamespace

import pytest

from app.core.error_codes import INVALID_EMBEDDING_RESPONSE
from app.core.exceptions import AppException
from app.repositories import regulation_chunk_repository


class FakeSession:
    """실제 DB 없이 add/flush/refresh에 전달된 ORM 객체만 확인하기 위한 테스트 더블입니다."""

    def __init__(self) -> None:
        self.added: list[object] = []
        self.flush_called = False
        self.refresh_called_values: list[object] = []
        self.executed_statements: list[object] = []
        self.executed_params: list[dict] = []

    def add(self, value) -> None:
        self.added.append(value)

    def flush(self) -> None:
        self.flush_called = True
        for index, value in enumerate(self.added, start=1):
            value.regulation_chunk_id = index

    def refresh(self, value) -> None:
        self.refresh_called_values.append(value)

    def execute(self, statement, params):
        self.executed_statements.append(statement)
        self.executed_params.append(params)
        return SimpleNamespace(rowcount=len(params["regulation_chunk_ids"]))


def test_create_regulation_chunks_for_document_maps_document_fields_to_model() -> None:
    db = FakeSession()
    regulation_document = SimpleNamespace(
        regulation_document_id=7,
        document_id="dorm-rule-001",
        document_version="2026.04",
        content="생활관 외박 신청은 통합 포털에서 처리한다.",
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
    assert "to_tsvector" in str(regulation_chunk.search_tsvector)
    assert regulation_chunk.embedding_model == "text-embedding-3-small"
    assert db.flush_called is True
    assert db.executed_params == []
    assert db.executed_statements == []
    assert db.refresh_called_values == [regulation_chunk]


def test_create_regulation_chunks_for_document_rejects_embedding_count_mismatch() -> None:
    db = FakeSession()
    regulation_document = SimpleNamespace(
        regulation_document_id=7,
        document_id="dorm-rule-001",
        document_version="2026.04",
        content="생활관 외박 신청은 통합 포털에서 처리한다.",
        keywords=["외박", "외출"],
    )
    regulation_chunk_repository.get_settings = lambda: SimpleNamespace(
        openai_embedding_model="text-embedding-3-small"
    )

    with pytest.raises(AppException) as exc_info:
        regulation_chunk_repository.create_regulation_chunks_for_document(
            db=db,
            regulation_document=regulation_document,
            chunk_texts=["첫 번째 청크", "두 번째 청크"],
            embeddings=[[0.1] * 1536],
        )

    assert exc_info.value.error_code == INVALID_EMBEDDING_RESPONSE
    assert db.added == []
    assert db.flush_called is False


def test_count_chunks_for_document_uses_count_query() -> None:
    executed_statements: list[object] = []

    class CountSession:
        def execute(self, statement):
            executed_statements.append(statement)
            return SimpleNamespace(scalar=lambda: 3)

    result = regulation_chunk_repository.count_chunks_for_document(CountSession(), 7)

    assert result == 3
    assert len(executed_statements) == 1


def test_search_hybrid_chunks_maps_hybrid_score_to_similarity() -> None:
    executed_params: list[dict] = []
    executed_statements: list[object] = []

    class MappingResult:
        def mappings(self):
            return self

        def all(self):
            return [
                SimpleNamespace(
                    regulation_chunk_id=1001,
                    document_id="dorm-rule",
                    document_version="v1",
                    chunk_id="chunk-1",
                    content="외박 신청은 포털에서 가능합니다.",
                    source="생활관 규정집",
                    source_url="https://example.com/rules/1",
                    dormitory="제1학생생활관",
                    vector_similarity=0.82,
                    vector_score=0.82,
                    keyword_score=0.4,
                    normalized_keyword_score=1.0,
                    vector_rank=2,
                    keyword_rank=1,
                    hybrid_score=0.874,
                )
            ]

    class HybridSession:
        def execute(self, statement, params):
            executed_statements.append(statement)
            executed_params.append(params)
            return MappingResult()

    result = regulation_chunk_repository.search_hybrid_chunks(
        db=HybridSession(),
        query_text="  외박 신청  ",
        query_embedding=[0.1, 0.2, 0.3],
        dormitory="제1학생생활관",
        top_k=3,
    )

    assert executed_params[0]["query_text"] == "외박 신청"
    assert executed_params[0]["dormitory"] == "제1학생생활관"
    executed_sql = str(executed_statements[0])
    assert "rc.search_tsvector" in executed_sql
    assert "to_tsvector(" not in executed_sql
    assert result[0]["similarity"] == 0.874
    assert result[0]["vector_similarity"] == 0.82
    assert result[0]["vector_score"] == 0.82
    assert result[0]["keyword_score"] == 0.4
    assert result[0]["normalized_keyword_score"] == 1.0


def test_search_hybrid_chunks_for_dormitories_passes_dormitory_list() -> None:
    executed_params: list[dict] = []

    class EmptyMappingResult:
        def mappings(self):
            return self

        def all(self):
            return []

    class HybridSession:
        def execute(self, _statement, params):
            executed_params.append(params)
            return EmptyMappingResult()

    result = regulation_chunk_repository.search_hybrid_chunks_for_dormitories(
        db=HybridSession(),
        query_text="택배",
        query_embedding=[0.1, 0.2, 0.3],
        dormitories=["제1학생생활관", "제2학생생활관"],
    )

    assert result == []
    assert executed_params[0]["dormitories"] == ["제1학생생활관", "제2학생생활관"]


def test_build_search_vector_text_joins_keywords_without_json_syntax() -> None:
    result = regulation_chunk_repository._build_search_vector_text(
        chunk_text="외박 신청",
        document_content="통합 포털에서 신청합니다.",
        keywords=["외박", "외출"],
    )

    assert result == "외박 신청 통합 포털에서 신청합니다. 외박 외출"
    assert "[" not in result
    assert "]" not in result
