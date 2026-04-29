from typing import Optional
from typing import Literal
from datetime import datetime

from pydantic import BaseModel
from pydantic import Field


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    question: str
    dormitory: Optional[str] = None


class ChatResponse(BaseModel):
    chat_log_id: int
    session_id: str
    answer: str
    answer_status: str
    source_url: str


class ChatSessionCreateRequest(BaseModel):
    user_id: Optional[int] = Field(default=None, ge=1)
    entry_point: Optional[Literal["WEB", "APP", "NOTICE", "FAQ"]] = None
    is_returning_user: bool = False
    utm_source: Optional[str] = Field(default=None, max_length=100)
    utm_medium: Optional[str] = Field(default=None, max_length=100)
    utm_campaign: Optional[str] = Field(default=None, max_length=100)


class ChatSessionCreateResponse(BaseModel):
    session_id: str
    user_id: Optional[int] = None
    total_turns: int
    started_at: datetime
    ended_at: Optional[datetime] = None
    last_activity_at: datetime
    entry_point: Optional[str] = None
    is_returning_user: bool
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    created_at: datetime
