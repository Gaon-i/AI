"""regulation_document CRUD와 자동 청킹/임베딩을 조합하는 서비스 파일입니다."""

from sqlalchemy.orm import Session

from app.core.error_codes import REGULATION_DOCUMENT_ALREADY_EXISTS
from app.core.error_codes import REGULATION_DOCUMENT_CREATE_FAILED
from app.core.error_codes import REGULATION_DOCUMENT_DELETE_FAILED
from app.core.error_codes import REGULATION_DOCUMENT_NOT_FOUND
from app.core.error_codes import REGULATION_DOCUMENT_UPDATE_FAILED
from app.core.exceptions import AppException
from app.core.time_utils import get_current_kst_time
from app.repositories.regulation_document_repository import activate_regulation_document
from app.repositories.regulation_document_repository import create_regulation_document
from app.repositories.regulation_document_repository import deactivate_other_document_versions
from app.repositories.regulation_document_repository import find_active_regulation_documents_by_document_id
from app.repositories.regulation_document_repository import find_regulation_document_by_document_key
from app.repositories.regulation_document_repository import find_regulation_document_by_id
from app.repositories.regulation_document_repository import mark_regulation_document_deleted
from app.repositories.regulation_document_repository import update_regulation_document
from app.repositories.regulation_chunk_repository import create_regulation_chunks_for_document
from app.repositories.regulation_chunk_repository import deactivate_chunks_for_document
from app.repositories.regulation_chunk_repository import deactivate_chunks_for_documents
from app.schemas.regulation_document import RegulationDocumentCommandResult
from app.schemas.regulation_document import RegulationDocumentCreateRequest
from app.schemas.regulation_document import RegulationDocumentSummary
from app.schemas.regulation_document import RegulationDocumentUpdateRequest
from app.services.embedding_service import create_embeddings_batch


def create_regulation_document_with_ingestion(
    db: Session,
    payload: RegulationDocumentCreateRequest,
) -> RegulationDocumentCommandResult:
    try:
        if (
            find_regulation_document_by_document_key(db, payload.document_id, payload.document_version)
            is not None
        ):
            raise AppException(REGULATION_DOCUMENT_ALREADY_EXISTS)

        regulation_document = create_regulation_document(db, payload)
        db.commit()
        db.refresh(regulation_document)
    except AppException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise AppException(REGULATION_DOCUMENT_CREATE_FAILED) from exc

    previous_active_documents = find_active_regulation_documents_by_document_id(db, payload.document_id)
    ingestion_status, ingested_chunk_count, deactivated_chunk_count = _run_ingestion_event(
        db,
        regulation_document,
        previous_active_documents=previous_active_documents,
    )
    return RegulationDocumentCommandResult(
        document=_to_document_summary(regulation_document),
        triggered_action="document_created",
        ingestion_status=ingestion_status,
        ingested_chunk_count=ingested_chunk_count,
        deactivated_chunk_count=deactivated_chunk_count,
    )


def update_regulation_document_with_ingestion(
    db: Session,
    regulation_document_id: int,
    payload: RegulationDocumentUpdateRequest,
) -> RegulationDocumentCommandResult:
    try:
        regulation_document = _get_regulation_document_or_raise(db, regulation_document_id)
        if regulation_document.is_deleted:
            raise AppException(REGULATION_DOCUMENT_NOT_FOUND)

        should_reingest = _should_reingest(regulation_document, payload)
        updated_document = update_regulation_document(regulation_document, payload)
        db.commit()
        db.refresh(updated_document)
    except AppException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise AppException(REGULATION_DOCUMENT_UPDATE_FAILED) from exc

    ingestion_status = None
    ingested_chunk_count = None
    deactivated_chunk_count = None
    if should_reingest:
        ingestion_status, ingested_chunk_count, deactivated_chunk_count = _run_reingestion_event(
            db,
            updated_document,
        )

    return RegulationDocumentCommandResult(
        document=_to_document_summary(updated_document),
        triggered_action="document_updated",
        ingestion_status=ingestion_status,
        ingested_chunk_count=ingested_chunk_count,
        deactivated_chunk_count=deactivated_chunk_count,
    )


def delete_regulation_document(
    db: Session,
    regulation_document_id: int,
) -> RegulationDocumentCommandResult:
    try:
        regulation_document = _get_regulation_document_or_raise(db, regulation_document_id)
        if regulation_document.is_deleted:
            raise AppException(REGULATION_DOCUMENT_NOT_FOUND)

        deactivated_chunk_count = deactivate_chunks_for_document(
            db,
            regulation_document.regulation_document_id,
        )
        deleted_document = mark_regulation_document_deleted(
            regulation_document,
            deleted_at=get_current_kst_time(),
        )
        db.commit()
        db.refresh(deleted_document)
    except AppException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise AppException(REGULATION_DOCUMENT_DELETE_FAILED) from exc

    return RegulationDocumentCommandResult(
        document=_to_document_summary(deleted_document),
        triggered_action="document_deleted",
        deactivated_chunk_count=deactivated_chunk_count,
    )


def _run_ingestion_event(db: Session, regulation_document, previous_active_documents) -> tuple[str, int, int]:
    try:
        chunk_texts = _chunk_document_content(regulation_document)
        embeddings = create_embeddings_batch(chunk_texts)
        created_chunks = create_regulation_chunks_for_document(
            db,
            regulation_document=regulation_document,
            chunk_texts=chunk_texts,
            embeddings=embeddings,
        )
        activate_regulation_document(regulation_document)
        previous_document_ids = deactivate_other_document_versions(
            db,
            document_id=regulation_document.document_id,
            active_document_id=regulation_document.regulation_document_id,
            deactivated_at=get_current_kst_time(),
        )
        deactivated_chunk_count = deactivate_chunks_for_documents(db, previous_document_ids)
        db.commit()
        db.refresh(regulation_document)
        return "succeeded", len(created_chunks), deactivated_chunk_count
    except Exception:
        db.rollback()
        return "failed", 0, 0


def _run_reingestion_event(db: Session, regulation_document) -> tuple[str, int, int]:
    try:
        deactivated_chunk_count = deactivate_chunks_for_document(
            db,
            regulation_document.regulation_document_id,
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
        db.refresh(regulation_document)
        return "succeeded", len(created_chunks), deactivated_chunk_count
    except Exception:
        db.rollback()
        return "failed", 0, 0


def _chunk_document_content(regulation_document) -> list[str]:
    content = (regulation_document.content or "").strip()
    title = (regulation_document.title or "").strip()
    if not content:
        return [f"제목: {title}".strip()]

    normalized_lines = [
        line.strip()
        for line in content.splitlines()
        if line.strip()
    ]
    paragraphs = normalized_lines or [content]

    chunks: list[str] = []
    buffer = ""
    for paragraph in paragraphs:
        candidate = f"{buffer}\n{paragraph}".strip() if buffer else paragraph
        if len(candidate) <= 800:
            buffer = candidate
            continue

        if buffer:
            chunks.append(_build_chunk_text(regulation_document, buffer))
        buffer = paragraph

    if buffer:
        chunks.append(_build_chunk_text(regulation_document, buffer))

    return chunks


def _build_chunk_text(regulation_document, content: str) -> str:
    parts: list[str] = []
    if regulation_document.dormitory:
        parts.append(f"생활관: {regulation_document.dormitory}")
    if regulation_document.category:
        parts.append(f"카테고리: {regulation_document.category}")
    if regulation_document.title:
        parts.append(f"제목: {regulation_document.title}")
    parts.append(f"본문: {content.strip()}")
    if regulation_document.source:
        parts.append(f"출처: {regulation_document.source}")
    if regulation_document.source_url:
        parts.append(f"출처 URL: {regulation_document.source_url}")
    if regulation_document.source_type:
        parts.append(f"출처유형: {regulation_document.source_type}")
    return "\n".join(parts)


def _get_regulation_document_or_raise(db: Session, regulation_document_id: int):
    regulation_document = find_regulation_document_by_id(db, regulation_document_id)
    if regulation_document is None:
        raise AppException(REGULATION_DOCUMENT_NOT_FOUND)
    return regulation_document


def _should_reingest(regulation_document, payload: RegulationDocumentUpdateRequest) -> bool:
    content_fields = ("title", "content", "category", "dormitory", "source", "source_url", "source_type")
    for field_name in content_fields:
        new_value = getattr(payload, field_name)
        if new_value is None:
            continue
        current_value = getattr(regulation_document, field_name)
        compare_value = str(new_value) if field_name == "source_url" else (
            new_value.value if field_name == "source_type" else new_value
        )
        if current_value != compare_value:
            return True
    return False


def _to_document_summary(regulation_document) -> RegulationDocumentSummary:
    return RegulationDocumentSummary(
        regulation_document_id=regulation_document.regulation_document_id,
        document_id=regulation_document.document_id,
        document_version=regulation_document.document_version,
        category=regulation_document.category,
        dormitory=regulation_document.dormitory,
        title=regulation_document.title,
        content=regulation_document.content,
        source=regulation_document.source,
        source_url=regulation_document.source_url,
        source_type=regulation_document.source_type,
        is_active=regulation_document.is_active,
        deactivated_at=regulation_document.deactivated_at,
        is_deleted=regulation_document.is_deleted,
        created_at=regulation_document.created_at,
        updated_at=regulation_document.updated_at,
    )
