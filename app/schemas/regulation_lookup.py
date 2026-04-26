from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RegulationLookupDocument(BaseModel):
    regulation_document_id: int
    document_id: str
    document_version: str
    document_type: str
    category: Optional[str] = None
    dormitory: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    keywords: Optional[list[str]] = None
    source_type: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class RegulationLookupResult(BaseModel):
    document_type: str
    total_count: int
    items: list[RegulationLookupDocument]


class RegulationDocumentTypeSummary(BaseModel):
    document_type: str
    document_count: int


class RegulationDocumentTypeListResult(BaseModel):
    items: list[RegulationDocumentTypeSummary]
