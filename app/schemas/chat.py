from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    question: str
    dormitory: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    source_url: str