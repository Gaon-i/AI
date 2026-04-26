from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.chat import ChatSessionCreateRequest, ChatSessionCreateResponse
from app.services.chat_service import answer_chat_question
from app.services.chat_session_service import start_chat_session
from app.db.session import get_db

router = APIRouter(prefix="/ai/chat", tags=["chat"])


@router.post(
    "/sessions",
    response_model=ChatSessionCreateResponse,
    summary="채팅 세션 시작",
    description=(
        "새로운 채팅 세션을 생성하고 `session_id`를 반환합니다.\n\n"
        "이후 질문 요청에서 이 세션 ID를 사용해 대화 로그와 사용자 활동을 연결할 수 있습니다."
    ),
)
def start_chat_session_api(
    request: ChatSessionCreateRequest,
    db: Session = Depends(get_db),
):
    return start_chat_session(db, request)


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    return answer_chat_question(db, request)
