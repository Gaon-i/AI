from typing import Optional
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


class ChatSessionCreateResponse(BaseModel):
    session_id: str
    user_id: Optional[int] = None
    total_turns: int
    started_at: datetime
    last_activity_at: datetime
