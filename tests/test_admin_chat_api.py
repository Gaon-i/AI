from fastapi.testclient import TestClient
from datetime import datetime

from app.api import admin_chat as admin_chat_module
from app.core.error_codes import CHAT_LOG_NOT_FOUND
from app.core.exceptions import AppException
from app.schemas.admin_chat import AdminChatLogDetail
from app.schemas.admin_chat import AdminChatReviewQueueItem
from app.schemas.admin_chat import AdminChatReviewQueueResult
from app.schemas.admin_chat import AdminChatSessionSummary
from app.schemas.admin_chat import AdminChatSessionsByDateResult


def test_get_admin_chat_log_api_returns_chat_log_detail(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        admin_chat_module,
        "get_admin_chat_log_detail",
        lambda *_args, **_kwargs: AdminChatLogDetail(
            chat_log_id=11,
            session_id="session-123",
            user_id=7,
            question="외박 신청은 어디서 하나요?",
            rewritten_query="외박 신청은 어디서 하나요?",
            answer="포털에서 신청하면 됩니다.",
            answer_status="SUCCESS",
            model_name="gpt-4o-mini",
            prompt_version="chat-answer-v1",
            retrieval_version="dormitory-search-v1",
            response_time=321,
            created_at="2026-04-27T10:00:00",
            retrieval_results=[
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
                }
            ],
            error_logs=[
                {
                    "error_id": 31,
                    "error_type": "LLM_API_ERROR",
                    "error_message": "llm failed",
                    "error_detail": "RuntimeError: llm failed",
                    "occurred_step": "ANSWER_GENERATION",
                    "created_at": datetime(2026, 4, 27, 10, 0, 2),
                }
            ],
        ),
    )

    response = client.get(
        "/api/v1/admin/chat/logs/11",
        headers={"X-Admin-Token": "test-admin-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": 200,
        "message": "chat log retrieved",
        "data": {
            "chat_log_id": 11,
            "session_id": "session-123",
            "user_id": 7,
            "question": "외박 신청은 어디서 하나요?",
            "rewritten_query": "외박 신청은 어디서 하나요?",
            "answer": "포털에서 신청하면 됩니다.",
            "answer_status": "SUCCESS",
            "model_name": "gpt-4o-mini",
            "prompt_version": "chat-answer-v1",
            "retrieval_version": "dormitory-search-v1",
            "response_time": 321,
            "created_at": "2026-04-27T10:00:00",
            "retrieval_results": [
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
                    "created_at": "2026-04-27T10:00:01",
                }
            ],
            "error_logs": [
                {
                    "error_id": 31,
                    "error_type": "LLM_API_ERROR",
                    "error_message": "llm failed",
                    "error_detail": "RuntimeError: llm failed",
                    "occurred_step": "ANSWER_GENERATION",
                    "created_at": "2026-04-27T10:00:02",
                }
            ],
        },
        "error_code": None,
    }


def test_get_admin_chat_log_api_returns_not_found_error(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        admin_chat_module,
        "get_admin_chat_log_detail",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AppException(CHAT_LOG_NOT_FOUND)),
    )

    response = client.get(
        "/api/v1/admin/chat/logs/999",
        headers={"X-Admin-Token": "test-admin-token"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "status": 404,
        "message": "chat log not found",
        "data": None,
        "error_code": "CHAT_LOG_NOT_FOUND",
    }


def test_get_admin_chat_review_queue_api_returns_paginated_queue(
    client: TestClient,
    monkeypatch,
) -> None:
    calls = {}

    def fake_get_admin_chat_review_queue(_db, **kwargs):
        calls.update(kwargs)
        return AdminChatReviewQueueResult(
            page=1,
            size=20,
            total_count=1,
            total_pages=1,
            items=[
                AdminChatReviewQueueItem(
                    chat_log_id=101,
                    session_id="session-123",
                    user_id=7,
                    question="택배 어디서 받아?",
                    answer_preview="외박 신청은 생활관 홈페이지에서...",
                    answer_status="SUCCESS",
                    review_reason="NEGATIVE_FEEDBACK",
                    negative_feedback_count=1,
                    latest_feedback_reason_code="INCORRECT_ANSWER",
                    created_at="2026-04-30T10:00:00",
                )
            ],
        )

    monkeypatch.setattr(admin_chat_module, "get_admin_chat_review_queue", fake_get_admin_chat_review_queue)

    response = client.get(
        "/api/v1/admin/chat/review-queue?page=1&size=20&reason=NEGATIVE_FEEDBACK",
        headers={"X-Admin-Token": "test-admin-token"},
    )

    assert response.status_code == 200
    assert calls == {"page": 1, "size": 20, "reason": "NEGATIVE_FEEDBACK"}
    assert response.json() == {
        "status": 200,
        "message": "chat review queue retrieved",
        "data": {
            "page": 1,
            "size": 20,
            "total_count": 1,
            "total_pages": 1,
            "items": [
                {
                    "chat_log_id": 101,
                    "session_id": "session-123",
                    "user_id": 7,
                    "question": "택배 어디서 받아?",
                    "answer_preview": "외박 신청은 생활관 홈페이지에서...",
                    "answer_status": "SUCCESS",
                    "review_reason": "NEGATIVE_FEEDBACK",
                    "negative_feedback_count": 1,
                    "latest_feedback_reason_code": "INCORRECT_ANSWER",
                    "created_at": "2026-04-30T10:00:00",
                }
            ],
        },
        "error_code": None,
    }


def test_get_admin_chat_review_queue_api_accepts_missing_reason(
    client: TestClient,
    monkeypatch,
) -> None:
    calls = {}

    def fake_get_admin_chat_review_queue(_db, **kwargs):
        calls.update(kwargs)
        return AdminChatReviewQueueResult(
            page=1,
            size=20,
            total_count=0,
            total_pages=0,
            items=[],
        )

    monkeypatch.setattr(admin_chat_module, "get_admin_chat_review_queue", fake_get_admin_chat_review_queue)

    response = client.get(
        "/api/v1/admin/chat/review-queue",
        headers={"X-Admin-Token": "test-admin-token"},
    )

    assert response.status_code == 200
    assert calls == {"page": 1, "size": 20, "reason": None}
    assert response.json()["data"]["items"] == []


def test_get_admin_chat_sessions_by_date_api_returns_paginated_sessions(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        admin_chat_module,
        "get_admin_chat_sessions_by_date",
        lambda *_args, **_kwargs: AdminChatSessionsByDateResult(
            date="2026-04-27",
            page=1,
            size=20,
            total_count=2,
            items=[
                AdminChatSessionSummary(
                    session_id="session-123",
                    user_id=7,
                    total_turns=3,
                    started_at="2026-04-27T09:30:00",
                    ended_at=None,
                    last_activity_at="2026-04-27T10:00:00",
                    created_at="2026-04-27T09:30:00",
                    is_expired=False,
                ),
                AdminChatSessionSummary(
                    session_id="session-456",
                    user_id=None,
                    total_turns=1,
                    started_at="2026-04-27T09:00:00",
                    ended_at=None,
                    last_activity_at="2026-04-27T09:10:00",
                    created_at="2026-04-27T09:00:00",
                    is_expired=True,
                ),
            ]
        ),
    )

    response = client.get(
        "/api/v1/admin/chat/sessions?date=2026-04-27&page=1&size=20",
        headers={"X-Admin-Token": "test-admin-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": 200,
        "message": "chat sessions retrieved",
        "data": {
            "date": "2026-04-27",
            "page": 1,
            "size": 20,
            "total_count": 2,
            "items": [
                {
                    "session_id": "session-123",
                    "user_id": 7,
                    "total_turns": 3,
                    "started_at": "2026-04-27T09:30:00",
                    "ended_at": None,
                    "last_activity_at": "2026-04-27T10:00:00",
                    "created_at": "2026-04-27T09:30:00",
                    "is_expired": False,
                },
                {
                    "session_id": "session-456",
                    "user_id": None,
                    "total_turns": 1,
                    "started_at": "2026-04-27T09:00:00",
                    "ended_at": None,
                    "last_activity_at": "2026-04-27T09:10:00",
                    "created_at": "2026-04-27T09:00:00",
                    "is_expired": True,
                },
            ]
        },
        "error_code": None,
    }
