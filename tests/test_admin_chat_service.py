from datetime import datetime

import pytest

from app.core.exceptions import AppException
from app.services import admin_chat_service


def test_get_admin_chat_log_detail_returns_mapped_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    chat_log = type(
        "ChatLogStub",
        (),
        {
            "chat_log_id": 11,
            "session_id": "session-123",
            "user_id": 7,
            "question": "외박 신청은 어디서 하나요?",
            "rewritten_query": "외박 신청은 어디서 하나요?",
            "answer": "포털에서 신청하면 됩니다.",
            "answer_status": type("StatusStub", (), {"value": "SUCCESS"})(),
            "model_name": "gpt-4o-mini",
            "prompt_version": "chat-answer-v1",
            "retrieval_version": "dormitory-search-v1",
            "response_time": 123,
            "created_at": datetime(2026, 4, 27, 10, 0, 0),
        },
    )()
    monkeypatch.setattr(admin_chat_service, "get_chat_log_by_id", lambda *_args, **_kwargs: chat_log)
    monkeypatch.setattr(
        admin_chat_service,
        "list_chat_retrieval_results_by_chat_log_id",
        lambda *_args, **_kwargs: [
            type(
                "ChatRetrievalResultStub",
                (),
                {
                    "chat_retrieval_result_id": 21,
                    "regulation_chunk_id": 1001,
                    "document_id": "dorm-rule",
                    "document_version": "v1",
                    "chunk_id": "chunk-1",
                    "retrieval_rank": 1,
                    "retrieval_score": 0.98,
                    "rerank_score": None,
                    "retrieval_method": "vector_dormitory_top_k",
                    "used_in_answer": True,
                    "selected_as_citation": False,
                    "citation_order": None,
                    "created_at": datetime(2026, 4, 27, 10, 0, 1),
                },
            )()
        ],
    )

    result = admin_chat_service.get_admin_chat_log_detail(object(), 11)

    assert result.chat_log_id == 11
    assert result.session_id == "session-123"
    assert result.answer_status == "SUCCESS"
    assert len(result.retrieval_results) == 1
    assert result.retrieval_results[0].regulation_chunk_id == 1001


def test_get_admin_chat_log_detail_raises_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin_chat_service, "get_chat_log_by_id", lambda *_args, **_kwargs: None)

    with pytest.raises(AppException) as exc_info:
        admin_chat_service.get_admin_chat_log_detail(object(), 999)

    assert exc_info.value.error_code.code == "CHAT_LOG_NOT_FOUND"


def test_get_recent_admin_chat_sessions_returns_up_to_10(monkeypatch: pytest.MonkeyPatch) -> None:
    sessions = [
        type(
            "ChatSessionStub",
            (),
            {
                "session_id": "session-123",
                "user_id": 7,
                "total_turns": 3,
                "started_at": datetime(2026, 4, 27, 9, 30, 0),
                "last_activity_at": datetime(2026, 4, 27, 10, 0, 0),
            },
        )(),
        type(
            "ChatSessionStub",
            (),
            {
                "session_id": "session-456",
                "user_id": None,
                "total_turns": 1,
                "started_at": datetime(2026, 4, 27, 9, 0, 0),
                "last_activity_at": datetime(2026, 4, 27, 9, 10, 0),
            },
        )(),
    ]
    monkeypatch.setattr(admin_chat_service, "list_recent_chat_sessions", lambda *_args, **_kwargs: sessions)

    result = admin_chat_service.get_recent_admin_chat_sessions(object())

    assert len(result.items) == 2
    assert result.items[0].session_id == "session-123"
    assert result.items[1].session_id == "session-456"
