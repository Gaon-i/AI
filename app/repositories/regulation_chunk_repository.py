"""regulation_chunk 저장 및 검색 책임을 분리한 repository 파일입니다."""

import hashlib
from datetime import datetime
from datetime import timezone
from uuid import uuid4

from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.error_codes import INVALID_EMBEDDING_RESPONSE
from app.core.exceptions import AppException
from app.db.models.regulation_document import RegulationDocument
from app.db.models.regulation_chunk import RegulationChunk


def create_regulation_chunks_for_document(
    db: Session,
    regulation_document: RegulationDocument,
    chunk_texts: list[str],
    embeddings: list[list[float]],
) -> list[RegulationChunk]:
    settings = get_settings()
    if len(chunk_texts) != len(embeddings):
        raise AppException(INVALID_EMBEDDING_RESPONSE)

    created_chunks: list[RegulationChunk] = []
    ingestion_suffix = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + uuid4().hex[:8]

    for index, (chunk_text, embedding) in enumerate(zip(chunk_texts, embeddings), start=1):
        chunk_id = (
            f"{regulation_document.document_id}"
            f":{regulation_document.document_version}"
            f":{ingestion_suffix}:{index}"
        )
        regulation_chunk = RegulationChunk(
            regulation_document_id=regulation_document.regulation_document_id,
            document_version=regulation_document.document_version,
            chunk_id=chunk_id,
            chunk_index=index - 1,
            chunk_text=chunk_text,
            keywords=regulation_document.keywords,
            chunk_hash=hashlib.sha256(chunk_text.encode("utf-8")).hexdigest(),
            embedding_model=settings.openai_embedding_model,
            embedding=embedding,
            is_active=True,
        )
        db.add(regulation_chunk)
        created_chunks.append(regulation_chunk)

    db.flush()
    refresh_search_vectors_for_chunks(
        db,
        [
            regulation_chunk.regulation_chunk_id
            for regulation_chunk in created_chunks
            if regulation_chunk.regulation_chunk_id is not None
        ],
    )
    for regulation_chunk in created_chunks:
        db.refresh(regulation_chunk)
    return created_chunks


def refresh_search_vectors_for_chunks(db: Session, regulation_chunk_ids: list[int]) -> int:
    """저장된 청크 검색 텍스트를 tsvector 컬럼에 반영합니다."""

    if not regulation_chunk_ids:
        return 0

    result = db.execute(
        text(
            """
            UPDATE regulation_chunk AS rc
            SET search_tsvector = to_tsvector(
                'simple',
                COALESCE(rc.chunk_text, '') || ' ' ||
                COALESCE(rd.content, '') || ' ' ||
                COALESCE(rc.keywords::text, '')
            )
            FROM regulation_document AS rd
            WHERE rd.regulation_document_id = rc.regulation_document_id
              AND rc.regulation_chunk_id = ANY(:regulation_chunk_ids)
            """
        ),
        {"regulation_chunk_ids": regulation_chunk_ids},
    )
    return result.rowcount or 0


def deactivate_chunks_for_document(db: Session, regulation_document_id: int) -> int:
    statement = (
        update(RegulationChunk)
        .where(
            RegulationChunk.regulation_document_id == regulation_document_id,
            RegulationChunk.is_active.is_(True),
        )
        .values(is_active=False)
    )
    return db.execute(statement).rowcount or 0


def count_chunks_for_document(db: Session, regulation_document_id: int) -> int:
    statement = select(func.count()).select_from(RegulationChunk).where(
        RegulationChunk.regulation_document_id == regulation_document_id
    )
    return db.execute(statement).scalar() or 0


def deactivate_chunks_for_documents(db: Session, regulation_document_ids: list[int]) -> int:
    if not regulation_document_ids:
        return 0

    statement = (
        update(RegulationChunk)
        .where(
            RegulationChunk.regulation_document_id.in_(regulation_document_ids),
            RegulationChunk.is_active.is_(True),
        )
        .values(is_active=False)
    )
    return db.execute(statement).rowcount or 0


def search_similar_chunks(
    db: Session,
    query_embedding: list[float],
    dormitory: str,
    top_k: int = 3,
):
    """질문 임베딩과 유사한 regulation_chunk를 pgvector로 검색합니다."""

    embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

    sql = text(
        """
        SELECT
            rc.regulation_chunk_id,
            rd.document_id,
            rd.document_version,
            rc.chunk_id,
            COALESCE(rc.chunk_text, rd.content, '') AS content,
            rd.source,
            rd.source_url,
            1 - (rc.embedding <=> CAST(:embedding AS vector)) AS similarity
        FROM regulation_chunk rc
        JOIN regulation_document rd
          ON rd.regulation_document_id = rc.regulation_document_id
        WHERE (rd.dormitory = :dormitory OR rd.dormitory IS NULL)
          AND rc.is_active = TRUE
          AND rd.is_active = TRUE
          AND rc.embedding IS NOT NULL
        ORDER BY rc.embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
        """
    )

    result = db.execute(
        sql,
        {
            "embedding": embedding_str,
            "dormitory": dormitory,
            "top_k": top_k,
        },
    ).mappings().all()

    return [
        {
            "regulation_chunk_id": row.regulation_chunk_id,
            "document_id": row.document_id,
            "document_version": row.document_version,
            "chunk_id": row.chunk_id,
            "content": row.content,
            "source": row.source,
            "source_url": row.source_url,
            "similarity": float(row.similarity),
        }
        for row in result
    ]


def search_similar_chunks_for_dormitories(
    db: Session,
    query_embedding: list[float],
    dormitories: list[str],
    top_k: int = 3,
):
    """여러 생활관과 공통 문서를 한 번의 pgvector 검색으로 조회합니다."""

    embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

    sql = text(
        """
        SELECT
            rc.regulation_chunk_id,
            rd.document_id,
            rd.document_version,
            rc.chunk_id,
            COALESCE(rc.chunk_text, rd.content, '') AS content,
            rd.source,
            rd.source_url,
            rd.dormitory,
            1 - (rc.embedding <=> CAST(:embedding AS vector)) AS similarity
        FROM regulation_chunk rc
        JOIN regulation_document rd
          ON rd.regulation_document_id = rc.regulation_document_id
        WHERE (rd.dormitory = ANY(:dormitories) OR rd.dormitory IS NULL)
          AND rc.is_active = TRUE
          AND rd.is_active = TRUE
          AND rc.embedding IS NOT NULL
        ORDER BY rc.embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
        """
    )

    result = db.execute(
        sql,
        {
            "embedding": embedding_str,
            "dormitories": dormitories,
            "top_k": top_k,
        },
    ).mappings().all()

    return [
        {
            "regulation_chunk_id": row.regulation_chunk_id,
            "document_id": row.document_id,
            "document_version": row.document_version,
            "chunk_id": row.chunk_id,
            "content": row.content,
            "source": row.source,
            "source_url": row.source_url,
            "retrieval_group": row.dormitory,
            "similarity": float(row.similarity),
        }
        for row in result
    ]


def search_similar_chunks_all_dormitories(
    db: Session,
    query_embedding: list[float],
    top_k: int = 5,
):
    """생활관 필터 없이 전체 활성 regulation_chunk를 대상으로 pgvector 검색합니다."""

    embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

    sql = text(
        """
        SELECT
            rc.regulation_chunk_id,
            rd.document_id,
            rd.document_version,
            rc.chunk_id,
            COALESCE(rc.chunk_text, rd.content, '') AS content,
            rd.source,
            rd.source_url,
            rd.dormitory,
            1 - (rc.embedding <=> CAST(:embedding AS vector)) AS similarity
        FROM regulation_chunk rc
        JOIN regulation_document rd
          ON rd.regulation_document_id = rc.regulation_document_id
        WHERE rc.is_active = TRUE
          AND rd.is_active = TRUE
          AND rc.embedding IS NOT NULL
        ORDER BY rc.embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
        """
    )

    result = db.execute(
        sql,
        {
            "embedding": embedding_str,
            "top_k": top_k,
        },
    ).mappings().all()

    return [
        {
            "regulation_chunk_id": row.regulation_chunk_id,
            "document_id": row.document_id,
            "document_version": row.document_version,
            "chunk_id": row.chunk_id,
            "content": row.content,
            "source": row.source,
            "source_url": row.source_url,
            "retrieval_group": row.dormitory,
            "similarity": float(row.similarity),
        }
        for row in result
    ]


def search_hybrid_chunks(
    db: Session,
    query_text: str,
    query_embedding: list[float],
    dormitory: str,
    top_k: int = 3,
    candidate_k: int = 20,
    keyword_weight: float = 0.3,
):
    """단일 생활관과 공통 문서를 대상으로 하이브리드 검색합니다."""

    return _search_hybrid_chunks(
        db=db,
        query_text=query_text,
        query_embedding=query_embedding,
        top_k=top_k,
        candidate_k=candidate_k,
        keyword_weight=keyword_weight,
        filter_sql="(rd.dormitory = :dormitory OR rd.dormitory IS NULL)",
        params={"dormitory": dormitory},
    )


def search_hybrid_chunks_for_dormitories(
    db: Session,
    query_text: str,
    query_embedding: list[float],
    dormitories: list[str],
    top_k: int = 3,
    candidate_k: int = 20,
    keyword_weight: float = 0.3,
):
    """여러 생활관과 공통 문서를 대상으로 하이브리드 검색합니다."""

    return _search_hybrid_chunks(
        db=db,
        query_text=query_text,
        query_embedding=query_embedding,
        top_k=top_k,
        candidate_k=candidate_k,
        keyword_weight=keyword_weight,
        filter_sql="(rd.dormitory = ANY(:dormitories) OR rd.dormitory IS NULL)",
        params={"dormitories": dormitories},
    )


def search_hybrid_chunks_all_dormitories(
    db: Session,
    query_text: str,
    query_embedding: list[float],
    top_k: int = 5,
    candidate_k: int = 30,
    keyword_weight: float = 0.3,
):
    """생활관 필터 없이 전체 활성 regulation_chunk를 대상으로 하이브리드 검색합니다."""

    return _search_hybrid_chunks(
        db=db,
        query_text=query_text,
        query_embedding=query_embedding,
        top_k=top_k,
        candidate_k=candidate_k,
        keyword_weight=keyword_weight,
        filter_sql="TRUE",
        params={},
    )


def _search_hybrid_chunks(
    db: Session,
    *,
    query_text: str,
    query_embedding: list[float],
    top_k: int,
    candidate_k: int,
    keyword_weight: float,
    filter_sql: str,
    params: dict,
):
    """
    벡터 유사도와 키워드 점수를 가중합해 검색합니다.

    반환값의 similarity는 최종 결합 점수이며, 벡터 단독 점수는 vector_similarity에 남깁니다.
    """

    embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

    sql = text(
        f"""
        WITH vector_search AS (
            SELECT
                rc.regulation_chunk_id,
                rd.document_id,
                rd.document_version,
                rc.chunk_id,
                COALESCE(rc.chunk_text, rd.content, '') AS content,
                rd.source,
                rd.source_url,
                rd.dormitory,
                1 - (rc.embedding <=> CAST(:embedding AS vector)) AS vector_similarity,
                NULL::float AS keyword_score,
                ROW_NUMBER() OVER (
                    ORDER BY rc.embedding <=> CAST(:embedding AS vector)
                ) AS vector_rank,
                NULL::bigint AS keyword_rank
            FROM regulation_chunk rc
            JOIN regulation_document rd
              ON rd.regulation_document_id = rc.regulation_document_id
            WHERE {filter_sql}
              AND rc.is_active = TRUE
              AND rd.is_active = TRUE
              AND rc.embedding IS NOT NULL
            ORDER BY rc.embedding <=> CAST(:embedding AS vector)
            LIMIT :candidate_k
        ),

        keyword_search AS (
            SELECT
                rc.regulation_chunk_id,
                rd.document_id,
                rd.document_version,
                rc.chunk_id,
                COALESCE(rc.chunk_text, rd.content, '') AS content,
                rd.source,
                rd.source_url,
                rd.dormitory,
                1 - (rc.embedding <=> CAST(:embedding AS vector)) AS vector_similarity,
                ts_rank_cd(
                    rc.search_tsvector,
                    websearch_to_tsquery('simple', :query_text)
                ) AS keyword_score,
                NULL::bigint AS vector_rank,
                ROW_NUMBER() OVER (
                    ORDER BY ts_rank_cd(
                        rc.search_tsvector,
                        websearch_to_tsquery('simple', :query_text)
                    ) DESC
                ) AS keyword_rank
            FROM regulation_chunk rc
            JOIN regulation_document rd
              ON rd.regulation_document_id = rc.regulation_document_id
            WHERE {filter_sql}
              AND rc.is_active = TRUE
              AND rd.is_active = TRUE
              AND rc.embedding IS NOT NULL
              AND rc.search_tsvector @@ websearch_to_tsquery('simple', :query_text)
            ORDER BY keyword_score DESC
            LIMIT :candidate_k
        ),

        combined AS (
            SELECT * FROM vector_search
            UNION ALL
            SELECT * FROM keyword_search
        ),

        dedup AS (
            SELECT
                regulation_chunk_id,
                MAX(document_id) AS document_id,
                MAX(document_version) AS document_version,
                MAX(chunk_id) AS chunk_id,
                MAX(content) AS content,
                MAX(source) AS source,
                MAX(source_url) AS source_url,
                MAX(dormitory) AS dormitory,
                MAX(vector_similarity) AS vector_similarity,
                MAX(keyword_score) AS keyword_score,
                MIN(vector_rank) AS vector_rank,
                MIN(keyword_rank) AS keyword_rank
            FROM combined
            GROUP BY regulation_chunk_id
        ),

        scored AS (
            SELECT
                *,
                LEAST(1, GREATEST(0, COALESCE(vector_similarity, 0))) AS vector_score,
                COALESCE(keyword_score / NULLIF(MAX(keyword_score) OVER (), 0), 0) AS normalized_keyword_score,
                (
                    LEAST(1, GREATEST(0, COALESCE(vector_similarity, 0))) +
                    (
                        :keyword_weight *
                        COALESCE(keyword_score / NULLIF(MAX(keyword_score) OVER (), 0), 0) *
                        (1 - LEAST(1, GREATEST(0, COALESCE(vector_similarity, 0))))
                    )
                ) AS hybrid_score
            FROM dedup
        )

        SELECT
            regulation_chunk_id,
            document_id,
            document_version,
            chunk_id,
            content,
            source,
            source_url,
            dormitory,
            vector_similarity,
            vector_score,
            keyword_score,
            normalized_keyword_score,
            vector_rank,
            keyword_rank,
            hybrid_score
        FROM scored
        ORDER BY hybrid_score DESC
        LIMIT :top_k
        """
    )

    result = db.execute(
        sql,
        {
            "embedding": embedding_str,
            "query_text": query_text.strip(),
            "top_k": top_k,
            "candidate_k": candidate_k,
            "keyword_weight": keyword_weight,
            **params,
        },
    ).mappings().all()

    return [
        {
            "regulation_chunk_id": row.regulation_chunk_id,
            "document_id": row.document_id,
            "document_version": row.document_version,
            "chunk_id": row.chunk_id,
            "content": row.content,
            "source": row.source,
            "source_url": row.source_url,
            "retrieval_group": row.dormitory,
            "similarity": float(row.hybrid_score),
            "vector_similarity": float(row.vector_similarity) if row.vector_similarity is not None else None,
            "vector_score": float(row.vector_score) if row.vector_score is not None else None,
            "keyword_score": float(row.keyword_score) if row.keyword_score is not None else None,
            "normalized_keyword_score": (
                float(row.normalized_keyword_score)
                if row.normalized_keyword_score is not None
                else None
            ),
            "vector_rank": int(row.vector_rank) if row.vector_rank is not None else None,
            "keyword_rank": int(row.keyword_rank) if row.keyword_rank is not None else None,
            "hybrid_score": float(row.hybrid_score),
        }
        for row in result
    ]
