from datetime import datetime

from app.schemas.chat import ChatSessionCreateRequest
from app.services import chat_session_service


class FakeSession:
    def __init__(self) -> None:
        self.commit_called = False
        self.refresh_called = False

    def commit(self) -> None:
        self.commit_called = True

    def refresh(self, _value) -> None:
        self.refresh_called = True


def test_start_chat_session_returns_created_session(monkeypatch) -> None:
    db = FakeSession()
    created_session = type(
        "ChatSessionStub",
        (),
        {
            "session_id": "session-123",
            "user_id": 7,
            "total_turns": 0,
            "started_at": datetime(2026, 4, 26, 10, 0, 0),
            "ended_at": None,
            "last_activity_at": datetime(2026, 4, 26, 10, 0, 0),
            "entry_point": "WEB",
            "is_returning_user": True,
            "utm_source": "newsletter",
            "utm_medium": "email",
            "utm_campaign": "spring",
            "created_at": datetime(2026, 4, 26, 10, 0, 0),
        },
    )()

    monkeypatch.setattr(
        chat_session_service,
        "create_chat_session",
        lambda *_args, **_kwargs: created_session,
    )

    result = chat_session_service.start_chat_session(
        db,
        ChatSessionCreateRequest(
            user_id=7,
            entry_point="WEB",
            is_returning_user=True,
            utm_source="newsletter",
            utm_medium="email",
            utm_campaign="spring",
        ),
    )

    assert result.session_id == "session-123"
    assert result.user_id == 7
    assert result.total_turns == 0
    assert result.entry_point == "WEB"
    assert result.is_returning_user is True
    assert result.utm_source == "newsletter"
    assert db.commit_called is True
    assert db.refresh_called is True
