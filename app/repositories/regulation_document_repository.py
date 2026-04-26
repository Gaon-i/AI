"""regulation_document CRUD 및 관리자용 조회 책임을 분리한 repository 파일입니다."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.db.models.regulation_document import RegulationDocument
from app.schemas.regulation_document import RegulationDocumentCreateRequest
from app.schemas.regulation_document import RegulationDocumentUpdateRequest


def find_regulation_document_by_id(
    db: Session,
    regulation_document_id: int,
) -> Optional[RegulationDocument]:
    statement = select(RegulationDocument).where(
        RegulationDocument.regulation_document_id == regulation_document_id
    )
    return db.execute(statement).scalar_one_or_none()


def find_regulation_document_by_document_key(
    db: Session,
    document_id: str,
    document_version: str,
) -> Optional[RegulationDocument]:
    statement = select(RegulationDocument).where(
        RegulationDocument.document_id == document_id,
        RegulationDocument.document_version == document_version,
    )
    return db.execute(statement).scalar_one_or_none()


def find_active_regulation_documents_by_document_id(
    db: Session,
    document_id: str,
) -> list[RegulationDocument]:
    statement = select(RegulationDocument).where(
        RegulationDocument.document_id == document_id,
        RegulationDocument.is_active.is_(True),
    )
    return list(db.execute(statement).scalars().all())


def create_regulation_document(
    db: Session,
    payload: RegulationDocumentCreateRequest,
) -> RegulationDocument:
    regulation_document = RegulationDocument(
        document_id=payload.document_id,
        document_version=payload.document_version,
        category=payload.category,
        dormitory=payload.dormitory,
        title=payload.title,
        content=payload.content,
        source=payload.source,
        source_url=str(payload.source_url) if payload.source_url else None,
        keywords=payload.keywords,
        source_type=payload.source_type.value,
        is_active=False,
    )
    db.add(regulation_document)
    db.flush()
    db.refresh(regulation_document)
    return regulation_document


def update_regulation_document(
    regulation_document: RegulationDocument,
    payload: RegulationDocumentUpdateRequest,
) -> RegulationDocument:
    if payload.category is not None:
        regulation_document.category = payload.category
    if payload.dormitory is not None:
        regulation_document.dormitory = payload.dormitory
    if payload.title is not None:
        regulation_document.title = payload.title
    if payload.content is not None:
        regulation_document.content = payload.content
    if payload.source is not None:
        regulation_document.source = payload.source
    if payload.source_url is not None:
        regulation_document.source_url = str(payload.source_url)
    if payload.keywords is not None:
        regulation_document.keywords = payload.keywords
    if payload.source_type is not None:
        regulation_document.source_type = payload.source_type.value
    return regulation_document


def deactivate_regulation_document(
    regulation_document: RegulationDocument,
) -> RegulationDocument:
    regulation_document.is_active = False
    return regulation_document


def activate_regulation_document(regulation_document: RegulationDocument) -> RegulationDocument:
    regulation_document.is_active = True
    return regulation_document


def deactivate_other_document_versions(
    db: Session,
    document_id: str,
    active_document_id: int,
) -> list[int]:
    statement = (
        update(RegulationDocument)
        .where(
            RegulationDocument.document_id == document_id,
            RegulationDocument.regulation_document_id != active_document_id,
            RegulationDocument.is_active.is_(True),
        )
        .values(is_active=False)
        .returning(RegulationDocument.regulation_document_id)
    )
    return list(db.execute(statement).scalars().all())
