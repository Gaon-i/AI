from fastapi import APIRouter
from fastapi import Depends
from fastapi import Path
from fastapi import status
from sqlalchemy.orm import Session

from app.api.dependencies.admin_auth import require_admin_token
from app.db.session import get_db
from app.schemas.admin_chat import AdminChatLogDetail
from app.schemas.admin_chat import AdminRecentChatSessionsResult
from app.schemas.common import ApiResponse
from app.services.admin_chat_service import get_admin_chat_log_detail
from app.services.admin_chat_service import get_recent_admin_chat_sessions

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
    "/sessions/recent",
    response_model=ApiResponse[AdminRecentChatSessionsResult],
    status_code=status.HTTP_200_OK,
    summary="최신 채팅 세션 10건 조회",
    description="관리자가 `chat_session` 테이블에서 최근 활동 기준 최신 10개 세션을 조회합니다.",
)
def get_recent_admin_chat_sessions_api(
    db: Session = Depends(get_db),
) -> ApiResponse[AdminRecentChatSessionsResult]:
    result = get_recent_admin_chat_sessions(db)
    return ApiResponse(
        status=status.HTTP_200_OK,
        message="recent chat sessions retrieved",
        data=result,
    )
