from pydantic import BaseModel


class NoticeRequest(BaseModel):
    title: str
    content: str


class NoticeResponse(BaseModel):
    summary: str