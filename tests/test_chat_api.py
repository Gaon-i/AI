from fastapi.testclient import TestClient

from app.api import chat as chat_module
from app.core.error_codes import CHAT_SESSION_EXPIRED
from app.core.exceptions import AppException
from app.schemas.chat import ChatResponse


def test_chat_api_returns_service_response(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        chat_module,
        "answer_chat_question",
        lambda *_args, **_kwargs: ChatResponse(
            chat_log_id=101,
            session_id="session-123",
            answer="생활관 규정에 따라 가능합니다.",
            answer_status="SUCCESS",
            source_url="https://example.com/rules/1",
        ),
    )

    response = client.post(
        "/api/v1/ai/chat",
        json={
            "session_id": "session-123",
            "question": "외박 신청은 어디서 하나요?",
            "dormitory": "제1학생생활관",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "chat_log_id": 101,
        "session_id": "session-123",
        "answer": "생활관 규정에 따라 가능합니다.",
        "answer_status": "SUCCESS",
        "source_url": "https://example.com/rules/1",
    }


def test_chat_api_returns_common_error_response_for_expired_session(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        chat_module,
        "answer_chat_question",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AppException(
                CHAT_SESSION_EXPIRED,
                detail="chat session expired after 30 minutes of inactivity. please start a new chat session",
            )
        ),
    )

    response = client.post(
        "/api/v1/ai/chat",
        json={
            "session_id": "session-123",
            "question": "외박 신청은 어디서 하나요?",
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "status": 409,
        "message": "chat session expired after 30 minutes of inactivity. please start a new chat session",
        "data": None,
        "error_code": "CHAT_SESSION_EXPIRED",
    }
