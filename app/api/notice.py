from datetime import datetime

from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.notice import NoticeRequest, NoticeResponse
from app.schemas.notice import NoticeListResult
from app.services.notice_sync_service import get_current_kst_time
from app.services.notice_sync_service import get_recent_notices_for_api
from app.services.summarizer import summarize_notice

router = APIRouter(tags=["notice"])


@router.post("/ai/notice_summary", response_model=NoticeResponse)
def summarize_notice_api(request: NoticeRequest):
    summary_data = summarize_notice(request.title, request.content)
    return NoticeResponse(
        title=request.title,
        summary=summary_data.summary,
        target_info=summary_data.target_info,
        schedule_info=summary_data.schedule_info,
        caution_info=summary_data.caution_info,
    )


@router.get(
    "/notices",
    response_model=NoticeListResult,
    summary="최근 공지 목록 조회",
    description="최근 30일 공지를 조회하고 이번 주/이번 달 건수를 함께 반환합니다.",
)
def get_recent_notices_api(db: Session = Depends(get_db)) -> NoticeListResult:
    return get_recent_notices_for_api(db=db, now=get_current_kst_time())
