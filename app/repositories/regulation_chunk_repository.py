"""regulation_chunk 및 regulation_document 저장 책임을 분리한 repository 파일입니다."""

import hashlib
from typing import Optional

from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.regulation_document import RegulationDocument
from app.db.models.regulation_chunk import RegulationChunk
from app.schemas.regulation_chunk import RegulationChunkCreateRequest


def find_by_chunk_id(db: Session, chunk_id: str) -> Optional[RegulationChunk]:
    """고유한 chunk_id로 기존 청크가 있는지 조회합니다."""

    statement = select(RegulationChunk).where(RegulationChunk.chunk_id == chunk_id)
    return db.execute(statement).scalar_one_or_none()


def find_existing_chunk_ids(db: Session, chunk_ids: list[str]) -> set[str]:
    """여러 chunk_id 중 이미 DB에 존재하는 값을 한 번의 조회로 가져옵니다."""

    if not chunk_ids:
        return set()

    statement = select(RegulationChunk.chunk_id).where(RegulationChunk.chunk_id.in_(chunk_ids))
    return set(db.execute(statement).scalars().all())


def create_regulation_chunk(
    db: Session,
    payload: RegulationChunkCreateRequest,
    chunk_text: str,
    embedding: list[float],
) -> RegulationChunk:
    """서비스에서 준비한 chunk_text와 embedding을 실제 DB row로 저장합니다."""

    regulation_document = _get_or_create_regulation_document(db, payload)
    settings = get_settings()
    regulation_chunk = RegulationChunk(
        regulation_document_id=regulation_document.regulation_document_id,
        document_version=payload.document_version,
        chunk_id=payload.chunk_id,
        chunk_index=payload.chunk_index,
        chunk_text=chunk_text,
        keywords=payload.keywords,
        chunk_hash=hashlib.sha256(chunk_text.encode("utf-8")).hexdigest(),
        embedding_model=settings.openai_embedding_model,
        embedding=embedding,
    )
    db.add(regulation_chunk)
    db.flush()
    db.refresh(regulation_chunk)
    return regulation_chunk


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
            rc.chunk_id,
            COALESCE(rc.chunk_text, rd.content, '') AS content,
            rd.source_url,
            1 - (rc.embedding <=> CAST(:embedding AS vector)) AS similarity
        FROM regulation_chunk rc
        JOIN regulation_document rd
          ON rd.regulation_document_id = rc.regulation_document_id
        WHERE (rd.dormitory = :dormitory OR rd.dormitory IS NULL)
          AND rc.is_active = TRUE
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
            "chunk_id": row.chunk_id,
            "content": row.content,
            "source_url": row.source_url,
            "similarity": float(row.similarity),
        }
        for row in result
    ]


def _get_or_create_regulation_document(
    db: Session,
    payload: RegulationChunkCreateRequest,
) -> RegulationDocument:
    statement = select(RegulationDocument).where(
        RegulationDocument.document_id == payload.document_id,
        RegulationDocument.document_version == payload.document_version,
    )
    regulation_document = db.execute(statement).scalar_one_or_none()

    if regulation_document is None:
        regulation_document = RegulationDocument(
            document_id=payload.document_id,
            document_version=payload.document_version,
        )
        db.add(regulation_document)

    regulation_document.category = payload.category
    regulation_document.dormitory = payload.dormitory
    regulation_document.title = payload.title
    regulation_document.content = payload.content
    regulation_document.source = payload.source
    regulation_document.source_url = str(payload.source_url) if payload.source_url else None
    regulation_document.source_type = payload.source_type.value

    db.flush()
    return regulation_document
