"""regulation_chunk 생성 API에서 사용하는 요청/응답 스키마를 모아둔 파일입니다."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import HttpUrl
from pydantic import field_validator


class RegulationChunkSourceType(str, Enum):
    """청크 출처 유형을 서버가 허용하는 값으로 제한합니다."""

    OFFICIAL = "official"
    COMMUNITY_TIP = "community_tip"


class RegulationChunkCreateRequest(BaseModel):
    """단건 청크 생성 요청 바디를 검증하는 스키마입니다."""

    document_id: str = Field(min_length=1, max_length=100)
    document_version: str = Field(min_length=1, max_length=50)
    chunk_id: str = Field(min_length=1, max_length=100)
    chunk_index: int = Field(ge=0)
    category: Optional[str] = None
    dormitory: Optional[str] = None
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    keywords: Optional[list[str]] = None
    source: Optional[str] = None
    source_url: Optional[HttpUrl] = None
    source_type: RegulationChunkSourceType

    @field_validator("document_id", "document_version", "chunk_id", "title", "content")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        """필수 문자열 필드는 공백만 들어오는 경우를 막고 trim 처리합니다."""

        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("must not be blank")
        return stripped_value

    @field_validator("category", "dormitory", "source")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        """선택 문자열 필드는 trim 후 비어 있으면 None으로 정규화합니다."""

        if value is None:
            return None

        stripped_value = value.strip()
        return stripped_value or None

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, value: Optional[list[str]]) -> Optional[list[str]]:
        """키워드 배열은 각 항목을 trim 하고 빈 값은 제거합니다."""

        if value is None:
            return None

        normalized_keywords = [keyword.strip() for keyword in value if keyword.strip()]
        if not normalized_keywords:
            return None

        return normalized_keywords


class RegulationChunkCreateResult(BaseModel):
    """단건 생성 성공 시 클라이언트에 돌려줄 최소 결과값입니다."""

    regulation_chunk_id: int
    regulation_document_id: int
    document_id: str
    document_version: str
    chunk_id: str
    chunk_index: int
    source_type: RegulationChunkSourceType


class RegulationChunkBulkCreateRequest(BaseModel):
    """벌크 생성용 요청 바디입니다."""

    items: list[RegulationChunkCreateRequest] = Field(min_length=1, max_length=20)


class RegulationChunkBulkCreateItemResult(BaseModel):
    """벌크 생성 결과에서 각 청크별 처리 상태를 표현합니다."""

    chunk_id: str
    status: str


class RegulationChunkBulkCreateResult(BaseModel):
    """벌크 생성 전체 결과를 감싸는 응답 스키마입니다."""

    created_count: int
    items: list[RegulationChunkBulkCreateItemResult]
