"""regulation_chunk 테이블에 대한 조회/저장 책임을 분리한 repository 파일입니다."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

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

    regulation_chunk = RegulationChunk(
        document_id=payload.document_id,
        chunk_id=payload.chunk_id,
        chunk_index=payload.chunk_index,
        category=payload.category,
        dormitory=payload.dormitory,
        title=payload.title,
        content=payload.content,
        chunk_text=chunk_text,
        keywords=payload.keywords,
        source=payload.source,
        source_url=str(payload.source_url) if payload.source_url else None,
        source_type=payload.source_type.value,
        embedding=embedding,
    )
    db.add(regulation_chunk)
    db.flush()
    db.refresh(regulation_chunk)
    return regulation_chunk
