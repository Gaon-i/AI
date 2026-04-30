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
    for regulation_chunk in created_chunks:
        db.refresh(regulation_chunk)
    return created_chunks


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