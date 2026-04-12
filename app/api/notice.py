from fastapi import APIRouter
from app.schemas.notice import NoticeRequest, NoticeResponse
from app.services.summarizer import summarize_notice

router = APIRouter(prefix="/ai/notice_summary", tags=["notice"])


@router.post("", response_model=NoticeResponse)
def summarize_notice_api(request: NoticeRequest):
    summary = summarize_notice(request.title, request.content)
    return NoticeResponse(summary=summary)