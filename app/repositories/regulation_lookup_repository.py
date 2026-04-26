from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.regulation_document import RegulationDocument


DOCUMENT_TYPE_REGEX = r"_[0-9]+$"


def list_active_regulation_documents_by_type(
    db: Session,
    document_type: str,
) -> list[RegulationDocument]:
    resolved_document_type = _document_type_expression()
    statement = (
        select(RegulationDocument)
        .where(
            resolved_document_type == document_type,
            RegulationDocument.is_active.is_(True),
        )
        .order_by(
            RegulationDocument.document_id.asc(),
            RegulationDocument.document_version.asc(),
            RegulationDocument.regulation_document_id.asc(),
        )
    )
    return list(db.execute(statement).scalars().all())


def list_active_regulation_document_types(
    db: Session,
) -> list[dict]:
    resolved_document_type = _document_type_expression()
    statement = (
        select(
            resolved_document_type.label("document_type"),
            func.count(RegulationDocument.regulation_document_id).label("document_count"),
        )
        .where(RegulationDocument.is_active.is_(True))
        .group_by(resolved_document_type)
        .order_by(resolved_document_type.asc())
    )
    return [
        {
            "document_type": row.document_type,
            "document_count": row.document_count,
        }
        for row in db.execute(statement).all()
    ]


def _document_type_expression():
    return func.regexp_replace(RegulationDocument.document_id, DOCUMENT_TYPE_REGEX, "")
