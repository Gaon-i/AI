from fastapi.testclient import TestClient

from app.api import chat as chat_module
from app.schemas.chat import ChatSessionCreateResponse


def test_start_chat_session_api_returns_created_response(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        chat_module,
        "start_chat_session",
        lambda *_args, **_kwargs: ChatSessionCreateResponse(
            session_id="session-123",
            user_id=7,
            total_turns=0,
            started_at="2026-04-26T10:00:00",
            ended_at=None,
            last_activity_at="2026-04-26T10:00:00",
            entry_point="WEB",
            is_returning_user=True,
            utm_source="newsletter",
            utm_medium="email",
            utm_campaign="spring",
            created_at="2026-04-26T10:00:00",
        ),
    )

    response = client.post(
        "/api/v1/ai/chat/sessions",
        json={
            "user_id": 7,
            "entry_point": "WEB",
            "is_returning_user": True,
            "utm_source": "newsletter",
            "utm_medium": "email",
            "utm_campaign": "spring",
        },
    )

    assert response.status_code == 200
    assert response.json()["session_id"] == "session-123"
    assert response.json()["user_id"] == 7
    assert response.json()["total_turns"] == 0
    assert response.json()["entry_point"] == "WEB"
    assert response.json()["is_returning_user"] is True


def test_start_chat_session_api_accepts_empty_body(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        chat_module,
        "start_chat_session",
        lambda *_args, **_kwargs: ChatSessionCreateResponse(
            session_id="session-456",
            user_id=None,
            total_turns=0,
            started_at="2026-04-26T10:00:00",
            ended_at=None,
            last_activity_at="2026-04-26T10:00:00",
            entry_point=None,
            is_returning_user=False,
            utm_source=None,
            utm_medium=None,
            utm_campaign=None,
            created_at="2026-04-26T10:00:00",
        ),
    )

    response = client.post(
        "/api/v1/ai/chat/sessions",
        json={},
    )

    assert response.status_code == 200
    assert response.json()["session_id"] == "session-456"
    assert response.json()["user_id"] is None
