"""청크 생성 비즈니스 흐름을 조합하는 서비스 파일입니다."""

from sqlalchemy.orm import Session

from app.core.error_codes import REGULATION_CHUNK_ALREADY_EXISTS
from app.core.error_codes import REGULATION_CHUNK_INGEST_FAILED
from app.core.error_codes import REGULATION_DOCUMENT_NOT_FOUND
from app.core.exceptions import AppException
from app.repositories.regulation_document_repository import find_regulation_document_by_id
from app.repositories.regulation_chunk_repository import count_chunks_for_document
from app.repositories.regulation_chunk_repository import create_regulation_chunks_for_document
from app.schemas.regulation_chunk import RegulationChunkBulkIngestionItemResult
from app.schemas.regulation_chunk import RegulationChunkBulkIngestionRequest
from app.schemas.regulation_chunk import RegulationChunkBulkIngestionResult
from app.schemas.regulation_chunk import RegulationChunkIngestionRequest
from app.schemas.regulation_chunk import RegulationChunkIngestionResult
from app.services.embedding_service import create_embeddings_batch
from app.services.regulation_document_service import _chunk_document_content


def ingest_regulation_chunks_for_document(
    db: Session,
    payload: RegulationChunkIngestionRequest,
) -> RegulationChunkIngestionResult:
    try:
        regulation_document = find_regulation_document_by_id(db, payload.regulation_document_id)
        if regulation_document is None:
            raise AppException(REGULATION_DOCUMENT_NOT_FOUND)

        if count_chunks_for_document(db, payload.regulation_document_id) > 0:
            raise AppException(
                REGULATION_CHUNK_ALREADY_EXISTS,
                detail="chunks already exist for regulation document",
            )

        chunk_texts = _chunk_document_content(regulation_document)
        embeddings = create_embeddings_batch(chunk_texts)
        created_chunks = create_regulation_chunks_for_document(
            db,
            regulation_document=regulation_document,
            chunk_texts=chunk_texts,
            embeddings=embeddings,
        )
        db.commit()
    except AppException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise AppException(REGULATION_CHUNK_INGEST_FAILED) from exc

    return RegulationChunkIngestionResult(
        regulation_document_id=regulation_document.regulation_document_id,
        document_id=regulation_document.document_id,
        document_version=regulation_document.document_version,
        created_count=len(created_chunks),
    )


def ingest_regulation_chunks_for_documents(
    db: Session,
    payload: RegulationChunkBulkIngestionRequest,
) -> RegulationChunkBulkIngestionResult:
    items: list[RegulationChunkBulkIngestionItemResult] = []
    for regulation_document_id in payload.regulation_document_ids:
        result = ingest_regulation_chunks_for_document(
            db,
            RegulationChunkIngestionRequest(regulation_document_id=regulation_document_id),
        )
        items.append(
            RegulationChunkBulkIngestionItemResult(
                regulation_document_id=result.regulation_document_id,
                created_count=result.created_count,
                status="created",
            )
        )
    return RegulationChunkBulkIngestionResult(
        created_document_count=len(items),
        items=items,
    )
