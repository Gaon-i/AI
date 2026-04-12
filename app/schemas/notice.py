from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator


class NoticeRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)

    @field_validator("title", "content")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("must not be blank")
        return stripped_value


class NoticeResponse(BaseModel):
    summary: str


class NoticeSummaryData(BaseModel):
    summary: str = Field(min_length=1)
    target_info: Optional[str] = None
    schedule_info: Optional[str] = None
    caution_info: Optional[str] = None
    generated_model: Optional[str] = None

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, value: str) -> str:
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("must not be blank")
        return stripped_value

    @field_validator("target_info", "schedule_info", "caution_info", "generated_model")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        stripped_value = value.strip()
        return stripped_value or None


class NoticeUpsertPayload(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    posted_at: datetime
    collected_at: Optional[datetime] = None

    @field_validator("title", "content", "source_url")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("must not be blank")
        return stripped_value


class NoticeListItem(BaseModel):
    notice_id: int
    title: str
    content: str
    source_url: str
    posted_at: datetime
    summary: Optional[str] = None
    target_info: Optional[str] = None
    schedule_info: Optional[str] = None
    caution_info: Optional[str] = None


class NoticeListResult(BaseModel):
    weekly_count: int
    monthly_count: int
    items: list[NoticeListItem]
