import pytest
from fastapi.testclient import TestClient

from app.api import chat as chat_module
from app.core.error_codes import CHAT_SESSION_EXPIRED
from app.core.exceptions import AppException
from app.schemas.chat import ChatFeedbackCreateResponse
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


def test_chat_feedback_api_returns_service_response(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        chat_module,
        "create_feedback",
        lambda *_args, **_kwargs: ChatFeedbackCreateResponse(
            feedback_id=501,
            chat_log_id=101,
            is_helpful=False,
            feedback_type="DISLIKE",
            reason_code="INCORRECT_ANSWER",
            feedback_comment="택배 위치를 물었는데 외박 안내가 나왔어요.",
            created_at="2026-04-30T10:00:00",
        ),
    )

    response = client.post(
        "/api/v1/ai/chat/feedback",
        json={
            "chat_log_id": 101,
            "is_helpful": False,
            "reason_code": "INCORRECT_ANSWER",
            "feedback_comment": "택배 위치를 물었는데 외박 안내가 나왔어요.",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "feedback_id": 501,
        "chat_log_id": 101,
        "is_helpful": False,
        "feedback_type": "DISLIKE",
        "reason_code": "INCORRECT_ANSWER",
        "feedback_comment": "택배 위치를 물었는데 외박 안내가 나왔어요.",
        "created_at": "2026-04-30T10:00:00",
    }


def test_chat_feedback_api_accepts_optional_reason_fields(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        chat_module,
        "create_feedback",
        lambda *_args, **_kwargs: ChatFeedbackCreateResponse(
            feedback_id=502,
            chat_log_id=101,
            is_helpful=True,
            feedback_type="LIKE",
            reason_code=None,
            feedback_comment=None,
            created_at="2026-04-30T10:00:00",
        ),
    )

    response = client.post(
        "/api/v1/ai/chat/feedback",
        json={
            "chat_log_id": 101,
            "is_helpful": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["reason_code"] is None
    assert response.json()["feedback_comment"] is None


def test_chat_feedback_api_rejects_positive_feedback_reason_fields(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        chat_module,
        "create_feedback",
        lambda *_args, **_kwargs: pytest.fail("invalid feedback should not call service"),
    )

    response = client.post(
        "/api/v1/ai/chat/feedback",
        json={
            "chat_log_id": 101,
            "is_helpful": True,
            "reason_code": "OTHER",
            "feedback_comment": "좋았지만 의견을 남깁니다.",
        },
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"
