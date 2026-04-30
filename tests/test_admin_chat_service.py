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
    monkeypatch.setattr(
        admin_chat_service,
        "list_chat_error_logs_by_chat_log_id",
        lambda *_args, **_kwargs: [
            type(
                "ChatErrorLogStub",
                (),
                {
                    "error_id": 31,
                    "error_type": "LLM_API_ERROR",
                    "error_message": "llm failed",
                    "error_detail": "RuntimeError: llm failed",
                    "occurred_step": "ANSWER_GENERATION",
                    "created_at": datetime(2026, 4, 27, 10, 0, 2),
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
    assert len(result.error_logs) == 1
    assert result.error_logs[0].error_type == "LLM_API_ERROR"


def test_get_admin_chat_log_detail_raises_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin_chat_service, "get_chat_log_by_id", lambda *_args, **_kwargs: None)

    with pytest.raises(AppException) as exc_info:
        admin_chat_service.get_admin_chat_log_detail(object(), 999)

    assert exc_info.value.error_code.code == "CHAT_LOG_NOT_FOUND"


def test_get_admin_chat_sessions_by_date_returns_paginated_sessions(monkeypatch: pytest.MonkeyPatch) -> None:
    sessions = [
        type(
            "ChatSessionStub",
            (),
            {
                "session_id": "session-123",
                "user_id": 7,
                "total_turns": 3,
                "started_at": datetime(2026, 4, 27, 9, 30, 0),
                "ended_at": None,
                "last_activity_at": datetime(2026, 4, 27, 10, 0, 0),
                "created_at": datetime(2026, 4, 27, 9, 30, 0),
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
                "ended_at": None,
                "last_activity_at": datetime(2026, 4, 27, 9, 10, 0),
                "created_at": datetime(2026, 4, 27, 9, 0, 0),
            },
        )(),
    ]
    list_calls: dict[str, object] = {}
    monkeypatch.setattr(admin_chat_service, "count_chat_sessions_by_started_date", lambda *_args, **_kwargs: 12)
    monkeypatch.setattr(
        admin_chat_service,
        "list_chat_sessions_by_started_date",
        lambda *_args, **kwargs: list_calls.update(kwargs) or sessions,
    )
    monkeypatch.setattr(admin_chat_service, "get_settings", lambda: type("SettingsStub", (), {"chat_session_timeout_minutes": 30})())
    monkeypatch.setattr(admin_chat_service, "get_current_utc_time", lambda: datetime(2026, 4, 27, 10, 0, 1))

    result = admin_chat_service.get_admin_chat_sessions_by_date(
        object(),
        target_date=datetime(2026, 4, 27).date(),
        page=2,
        size=10,
    )

    assert result.date == datetime(2026, 4, 27).date()
    assert result.page == 2
    assert result.size == 10
    assert result.total_count == 12
    assert list_calls == {"offset": 10, "limit": 10}
    assert len(result.items) == 2
    assert result.items[0].session_id == "session-123"
    assert result.items[1].session_id == "session-456"
    assert result.items[0].is_expired is False
    assert result.items[1].is_expired is True
