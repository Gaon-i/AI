from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas.chat import ChatFeedbackCreateRequest, ChatFeedbackCreateResponse
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.chat import ChatSessionCreateRequest, ChatSessionCreateResponse
from app.services.chat_feedback_service import create_feedback
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


@router.post(
    "/feedback",
    response_model=ChatFeedbackCreateResponse,
    summary="챗봇 답변 피드백 저장",
    description=(
        "특정 `chat_log_id`에 대해 사용자가 답변이 도움이 되었는지 저장합니다.\n\n"
        "`reason_code`와 `feedback_comment`는 선택값이며, 불만족 사유나 추가 의견이 있을 때만 전달합니다.\n\n"
        "reason_code 목록:\n"
        "- `INCORRECT_ANSWER`: 답변이 질문과 다르거나 틀림\n"
        "- `BAD_CITATION`: 근거/출처가 부정확함\n"
        "- `TOO_LONG`: 답변이 너무 김\n"
        "- `TOO_VAGUE`: 답변이 모호함\n"
        "- `OUTDATED_INFO`: 정보가 오래됨\n"
        "- `NO_SOURCE`: 출처가 없음\n"
        "- `OTHER`: 기타"
    ),
)
def create_chat_feedback_api(
    request: ChatFeedbackCreateRequest,
    db: Session = Depends(get_db),
):
    return create_feedback(db, request)


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    return answer_chat_question(db, request)
