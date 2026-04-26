from typing import Optional
from datetime import datetime

from pydantic import BaseModel
from pydantic import Field

class ChatRequest(BaseModel):
    question: str
    dormitory: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    source_url: str


class ChatSessionCreateRequest(BaseModel):
    user_id: Optional[int] = Field(default=None, ge=1)


class ChatSessionCreateResponse(BaseModel):
    session_id: str
    user_id: Optional[int] = None
    total_turns: int
    started_at: datetime
    last_activity_at: datetime
