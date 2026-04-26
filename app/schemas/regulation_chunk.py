"""regulation_chunk 문서 기준 적재 API에서 사용하는 요청/응답 스키마입니다."""

from enum import Enum

from pydantic import BaseModel
from pydantic import Field


class RegulationChunkSourceType(str, Enum):
    """문서/청크 출처 유형을 서버가 허용하는 값으로 제한합니다."""

    OFFICIAL = "official"
    COMMUNITY_TIP = "community_tip"


class RegulationChunkIngestionRequest(BaseModel):
    """문서 기준 단건 청크 적재 요청입니다."""

    regulation_document_id: int = Field(ge=1)


class RegulationChunkIngestionResult(BaseModel):
    """문서 기준 단건 청크 적재 결과입니다."""

    regulation_document_id: int
    document_id: str
    document_version: str
    created_count: int


class RegulationChunkBulkIngestionRequest(BaseModel):
    """문서 기준 벌크 청크 적재 요청입니다."""

    regulation_document_ids: list[int] = Field(min_length=1, max_length=20)


class RegulationChunkBulkIngestionItemResult(BaseModel):
    regulation_document_id: int
    created_count: int
    status: str


class RegulationChunkBulkIngestionResult(BaseModel):
    created_document_count: int
    items: list[RegulationChunkBulkIngestionItemResult]
