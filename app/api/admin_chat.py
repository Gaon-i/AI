from datetime import date

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Path
from fastapi import Query
from fastapi import status
from sqlalchemy.orm import Session

from app.api.dependencies.admin_auth import require_admin_token
from app.db.session import get_db
from app.schemas.admin_chat import AdminChatLogDetail
from app.schemas.admin_chat import AdminChatSessionsByDateResult
from app.schemas.common import ApiResponse
from app.services.admin_chat_service import get_admin_chat_sessions_by_date
from app.services.admin_chat_service import get_admin_chat_log_detail

router = APIRouter(
    prefix="/admin/chat",
    tags=["admin-chat"],
    dependencies=[Depends(require_admin_token)],
)


@router.get(
    "/logs/{chat_log_id}",
    response_model=ApiResponse[AdminChatLogDetail],
    status_code=status.HTTP_200_OK,
    summary="채팅 로그 단건 조회",
    description="관리자가 `chat_log_id` 기준으로 질문/답변 상태와 메타데이터를 조회합니다.",
)
def get_admin_chat_log_api(
    chat_log_id: int = Path(ge=1),
    db: Session = Depends(get_db),
) -> ApiResponse[AdminChatLogDetail]:
    result = get_admin_chat_log_detail(db, chat_log_id)
    return ApiResponse(
        status=status.HTTP_200_OK,
        message="chat log retrieved",
        data=result,
    )


@router.get(
    "/sessions",
    response_model=ApiResponse[AdminChatSessionsByDateResult],
    status_code=status.HTTP_200_OK,
    summary="날짜별 채팅 세션 조회",
    description="관리자가 `started_at` 기준 특정 날짜의 채팅 세션을 페이지 단위로 조회합니다.",
)
def get_admin_chat_sessions_by_date_api(
    target_date: date = Query(alias="date"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ApiResponse[AdminChatSessionsByDateResult]:
    result = get_admin_chat_sessions_by_date(db, target_date=target_date, page=page, size=size)
    return ApiResponse(
        status=status.HTTP_200_OK,
        message="chat sessions retrieved",
        data=result,
    )
