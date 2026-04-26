"""regulation_document 관리자 API에서 사용하는 요청/응답 스키마입니다."""

from datetime import datetime
from typing import Optional
from typing import Any

from pydantic import BaseModel
from pydantic import Field
from pydantic import HttpUrl
from pydantic import field_validator
from pydantic import model_validator

from app.schemas.regulation_chunk import RegulationChunkSourceType


class RegulationDocumentCreateRequest(BaseModel):
    document_id: str = Field(min_length=1, max_length=100)
    document_version: str = Field(min_length=1, max_length=50)
    category: Optional[str] = Field(default=None, max_length=50)
    dormitory: Optional[str] = Field(default=None, max_length=50)
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    source: Optional[str] = Field(default=None, max_length=255)
    source_url: Optional[HttpUrl] = None
    keywords: Optional[list[str]] = None
    source_type: RegulationChunkSourceType

    @field_validator("document_id", "document_version", "title", "content")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("must not be blank")
        return stripped_value

    @field_validator("category", "dormitory", "source")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        stripped_value = value.strip()
        return stripped_value or None

    @field_validator("keywords")
    @classmethod
    def normalize_keywords(cls, value: Optional[list[str]]) -> Optional[list[str]]:
        return _normalize_keywords(value)


class RegulationDocumentUpdateRequest(BaseModel):
    category: Optional[str] = Field(default=None, max_length=50)
    dormitory: Optional[str] = Field(default=None, max_length=50)
    title: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = Field(default=None, max_length=255)
    source_url: Optional[HttpUrl] = None
    keywords: Optional[list[str]] = None
    source_type: Optional[RegulationChunkSourceType] = None

    @field_validator("category", "dormitory", "title", "content", "source")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        stripped_value = value.strip()
        return stripped_value or None

    @field_validator("keywords")
    @classmethod
    def normalize_keywords(cls, value: Optional[list[str]]) -> Optional[list[str]]:
        return _normalize_keywords(value)

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "RegulationDocumentUpdateRequest":
        if not any(value is not None for value in self.model_dump().values()):
            raise ValueError("at least one field must be provided")
        return self


class RegulationDocumentSummary(BaseModel):
    regulation_document_id: int
    document_id: str
    document_version: str
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


class RegulationDocumentCommandResult(BaseModel):
    document: RegulationDocumentSummary
    triggered_action: str
    ingestion_status: Optional[str] = None
    ingestion_error_code: Optional[str] = None
    ingested_chunk_count: Optional[int] = None
    deactivated_chunk_count: Optional[int] = None


class RegulationDocumentBulkCreateRequest(BaseModel):
    items: list[RegulationDocumentCreateRequest] = Field(min_length=1, max_length=20)


class RegulationDocumentBulkCreateItemResult(BaseModel):
    status: str
    document_id: str
    document_version: str
    result: Optional[RegulationDocumentCommandResult] = None
    error_code: Optional[str] = None
    message: Optional[str] = None


class RegulationDocumentBulkCreateResult(BaseModel):
    total_count: int
    created_count: int
    failed_count: int
    items: list[RegulationDocumentBulkCreateItemResult]


def _normalize_keywords(value: Optional[list[Any]]) -> Optional[list[str]]:
    if value is None:
        return None

    normalized_keywords: list[str] = []
    seen_keywords: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            raise ValueError("keywords must be strings")

        normalized_keyword = item.strip()
        if not normalized_keyword:
            continue
        if normalized_keyword in seen_keywords:
            continue
        seen_keywords.add(normalized_keyword)
        normalized_keywords.append(normalized_keyword)

    return normalized_keywords
