from datetime import datetime

import pytest

from app.core.error_codes import CHAT_LOG_NOT_FOUND
from app.core.exceptions import AppException
from app.schemas.chat import ChatFeedbackCreateRequest
from app.services import chat_feedback_service


def test_create_feedback_stores_dislike_feedback(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {}
    chat_log = type("ChatLogStub", (), {"chat_log_id": 101, "user_id": 7})()
    created_at = datetime(2026, 4, 30, 10, 0, 0)
    feedback = type(
        "ChatFeedbackStub",
        (),
        {
            "feedback_id": 501,
            "chat_log_id": 101,
            "is_helpful": False,
            "feedback_type": "DISLIKE",
            "reason_code": "INCORRECT_ANSWER",
            "feedback_comment": "택배 위치를 물었는데 외박 안내가 나왔어요.",
            "created_at": created_at,
        },
    )()

    class FakeDb:
        def commit(self):
            calls["committed"] = True

        def refresh(self, item):
            calls["refreshed"] = item

    def fake_create_chat_feedback(_db, **kwargs):
        calls.update(kwargs)
        return feedback

    monkeypatch.setattr(chat_feedback_service, "get_chat_log_by_id", lambda *_args: chat_log)
    monkeypatch.setattr(chat_feedback_service, "create_chat_feedback", fake_create_chat_feedback)

    response = chat_feedback_service.create_feedback(
        FakeDb(),
        ChatFeedbackCreateRequest(
            chat_log_id=101,
            is_helpful=False,
            reason_code="INCORRECT_ANSWER",
            feedback_comment="택배 위치를 물었는데 외박 안내가 나왔어요.",
        ),
    )

    assert calls["chat_log_id"] == 101
    assert calls["user_id"] == 7
    assert calls["feedback_type"] == "DISLIKE"
    assert calls["is_helpful"] is False
    assert calls["reason_code"] == "INCORRECT_ANSWER"
    assert calls["feedback_comment"] == "택배 위치를 물었는데 외박 안내가 나왔어요."
    assert calls["committed"] is True
    assert calls["refreshed"] is feedback
    assert response.feedback_id == 501
    assert response.chat_log_id == 101
    assert response.is_helpful is False
    assert response.feedback_type == "DISLIKE"


def test_create_feedback_stores_like_feedback_without_optional_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {}
    chat_log = type("ChatLogStub", (), {"chat_log_id": 101, "user_id": None})()
    feedback = type(
        "ChatFeedbackStub",
        (),
        {
            "feedback_id": 502,
            "chat_log_id": 101,
            "is_helpful": True,
            "feedback_type": "LIKE",
            "reason_code": None,
            "feedback_comment": None,
            "created_at": datetime(2026, 4, 30, 10, 0, 0),
        },
    )()

    class FakeDb:
        def commit(self):
            calls["committed"] = True

        def refresh(self, item):
            calls["refreshed"] = item

    def fake_create_chat_feedback(_db, **kwargs):
        calls.update(kwargs)
        return feedback

    monkeypatch.setattr(chat_feedback_service, "get_chat_log_by_id", lambda *_args: chat_log)
    monkeypatch.setattr(chat_feedback_service, "create_chat_feedback", fake_create_chat_feedback)

    response = chat_feedback_service.create_feedback(
        FakeDb(),
        ChatFeedbackCreateRequest(chat_log_id=101, is_helpful=True),
    )

    assert calls["feedback_type"] == "LIKE"
    assert calls["reason_code"] is None
    assert calls["feedback_comment"] is None
    assert response.is_helpful is True
    assert response.feedback_type == "LIKE"


def test_create_feedback_raises_when_chat_log_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chat_feedback_service, "get_chat_log_by_id", lambda *_args: None)
    monkeypatch.setattr(
        chat_feedback_service,
        "create_chat_feedback",
        lambda *_args, **_kwargs: pytest.fail("missing chat log should not create feedback"),
    )

    with pytest.raises(AppException) as exc_info:
        chat_feedback_service.create_feedback(
            object(),
            ChatFeedbackCreateRequest(chat_log_id=999, is_helpful=False),
        )

    assert exc_info.value.error_code == CHAT_LOG_NOT_FOUND
