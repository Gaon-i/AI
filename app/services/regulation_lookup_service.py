from sqlalchemy.orm import Session

from app.repositories.regulation_lookup_repository import list_active_regulation_documents_by_type
from app.repositories.regulation_lookup_repository import list_active_regulation_document_types
from app.schemas.regulation_lookup import RegulationDocumentTypeListResult
from app.schemas.regulation_lookup import RegulationDocumentTypeSummary
from app.schemas.regulation_lookup import RegulationLookupDocument
from app.schemas.regulation_lookup import RegulationLookupResult


def get_regulation_documents_by_type(
    db: Session,
    document_type: str,
) -> RegulationLookupResult:
    normalized_document_type = document_type.strip()
    documents = list_active_regulation_documents_by_type(db, normalized_document_type)
    return RegulationLookupResult(
        document_type=normalized_document_type,
        total_count=len(documents),
        items=[_to_lookup_document(document) for document in documents],
    )


def get_regulation_document_types(db: Session) -> RegulationDocumentTypeListResult:
    return RegulationDocumentTypeListResult(
        items=[
            RegulationDocumentTypeSummary(
                document_type=item["document_type"],
                document_count=item["document_count"],
            )
            for item in list_active_regulation_document_types(db)
        ]
    )


def _to_lookup_document(document) -> RegulationLookupDocument:
    return RegulationLookupDocument(
        regulation_document_id=document.regulation_document_id,
        document_id=document.document_id,
        document_version=document.document_version,
        document_type=_extract_document_type(document.document_id),
        category=document.category,
        dormitory=document.dormitory,
        title=document.title,
        content=document.content,
        source=document.source,
        source_url=document.source_url,
        keywords=document.keywords,
        source_type=document.source_type,
        is_active=document.is_active,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def _extract_document_type(document_id: str) -> str:
    if "_" not in document_id:
        return document_id
    head, tail = document_id.rsplit("_", 1)
    return head if tail.isdigit() else document_id
