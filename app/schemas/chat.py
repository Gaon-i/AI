from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str
    dormitory: str


class ChatResponse(BaseModel):
    answer: str
    source_url: str