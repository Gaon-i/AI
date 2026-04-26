from datetime import datetime

import pytest

from app.core.exceptions import AppException
from app.db.models.chat_enums import ChatAnswerStatus
from app.schemas.chat import ChatRequest
from app.services import chat_service
from app.services.generator import AnswerGenerationResult


class FakeSession:
    def __init__(self) -> None:
        self.commit_count = 0
        self.flush_count = 0
        self.rollback_count = 0
        self.refreshed_objects: list[object] = []

    def commit(self) -> None:
        self.commit_count += 1

    def flush(self) -> None:
        self.flush_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1

    def refresh(self, value) -> None:
        self.refreshed_objects.append(value)


def _build_chat_session():
    return type(
        "ChatSessionStub",
        (),
        {
            "session_id": "session-123",
            "user_id": 7,
            "total_turns": 0,
            "last_activity_at": datetime(2026, 4, 27, 10, 0, 0),
        },
    )()


def _build_chat_log():
    return type(
        "ChatLogStub",
        (),
        {
            "chat_log_id": 501,
            "session_id": "session-123",
            "question": "외박 신청은 어디서 하나요?",
            "answer_status": ChatAnswerStatus.PROCESSING,
            "answer": None,
            "rewritten_query": None,
            "model_name": None,
            "prompt_version": None,
            "retrieval_version": None,
            "response_time": None,
        },
    )()


def test_answer_chat_question_returns_success_for_single_dormitory(monkeypatch: pytest.MonkeyPatch) -> None:
    db = FakeSession()
    chat_session = _build_chat_session()
    chat_log = _build_chat_log()

    retrieval_calls: dict[str, object] = {}

    monkeypatch.setattr(chat_service, "get_chat_session", lambda *_args, **_kwargs: chat_session)
    monkeypatch.setattr(chat_service, "create_chat_log", lambda *_args, **_kwargs: chat_log)
    monkeypatch.setattr(chat_service, "touch_chat_session_activity", lambda *_args, **_kwargs: chat_session)
    monkeypatch.setattr(chat_service, "validate_question", lambda *_args, **_kwargs: (True, "외박 신청은 어디서 하나요?"))
    monkeypatch.setattr(chat_service, "create_query_embedding", lambda *_args, **_kwargs: [0.1, 0.2, 0.3])
    monkeypatch.setattr(
        chat_service,
        "search_similar_chunks",
        lambda *_args, **_kwargs: [
            {
                "regulation_chunk_id": 1001,
                "document_id": "dorm-rule",
                "document_version": "v1",
                "chunk_id": "chunk-1",
                "content": "외박 신청은 포털에서 가능합니다.",
                "source_url": "https://example.com/rules/1",
                "similarity": 0.98,
            }
        ],
    )
    monkeypatch.setattr(
        chat_service,
        "generate_answer",
        lambda *_args, **_kwargs: AnswerGenerationResult(
            answer="포털에서 외박 신청을 하면 됩니다. [C1]",
            source_url="https://example.com/rules/1",
            cited_regulation_chunk_ids=[1001],
        ),
    )
    monkeypatch.setattr(
        chat_service,
        "create_chat_retrieval_results",
        lambda *_args, **kwargs: retrieval_calls.update(kwargs) or [],
    )
    monkeypatch.setattr(
        chat_service,
        "mark_chat_retrieval_results_used_in_answer",
        lambda *_args, **kwargs: retrieval_calls.update(
            {
                "mark_used_chat_log_id": kwargs["chat_log_id"],
                "cited_regulation_chunk_ids": kwargs["cited_regulation_chunk_ids"],
            }
        )
        or [],
    )

    response = chat_service.answer_chat_question(
        db,
        ChatRequest(
            session_id="session-123",
            question="외박 신청은 어디서 하나요?",
            dormitory="제1학생생활관",
        ),
    )

    assert response.chat_log_id == 501
    assert response.session_id == "session-123"
    assert response.answer == "포털에서 외박 신청을 하면 됩니다. [C1]"
    assert response.answer_status == "SUCCESS"
    assert response.source_url == "https://example.com/rules/1"
    assert chat_log.answer_status == ChatAnswerStatus.SUCCESS
    assert chat_log.rewritten_query == "외박 신청은 어디서 하나요?"
    assert chat_log.model_name == chat_service.ANSWER_MODEL_NAME
    assert chat_log.prompt_version == chat_service.PROMPT_VERSION_SINGLE
    assert chat_log.retrieval_version == chat_service.RETRIEVAL_VERSION_SINGLE
    assert retrieval_calls["chat_log_id"] == 501
    assert retrieval_calls["retrieval_method"] == chat_service.RETRIEVAL_METHOD_SINGLE
    assert retrieval_calls["retrieval_items"][0]["regulation_chunk_id"] == 1001
    assert retrieval_calls["retrieval_items"][0]["citation_label"] == "C1"
    assert retrieval_calls["mark_used_chat_log_id"] == 501
    assert retrieval_calls["cited_regulation_chunk_ids"] == [1001]
    assert db.commit_count == 2
    assert db.flush_count == 1
    assert db.rollback_count == 0


def test_answer_chat_question_returns_no_answer_for_invalid_question(monkeypatch: pytest.MonkeyPatch) -> None:
    db = FakeSession()
    chat_session = _build_chat_session()
    chat_log = _build_chat_log()

    monkeypatch.setattr(chat_service, "get_chat_session", lambda *_args, **_kwargs: chat_session)
    monkeypatch.setattr(chat_service, "create_chat_log", lambda *_args, **_kwargs: chat_log)
    monkeypatch.setattr(chat_service, "touch_chat_session_activity", lambda *_args, **_kwargs: chat_session)
    monkeypatch.setattr(chat_service, "validate_question", lambda *_args, **_kwargs: (False, "질문이 너무 짧습니다."))
    monkeypatch.setattr(
        chat_service,
        "create_chat_retrieval_results",
        lambda *_args, **_kwargs: pytest.fail("invalid question should not save retrieval results"),
    )

    response = chat_service.answer_chat_question(
        db,
        ChatRequest(
            session_id="session-123",
            question="?",
        ),
    )

    assert response.answer == chat_service.INVALID_QUESTION_MESSAGE
    assert response.answer_status == "NO_ANSWER"
    assert response.source_url == ""
    assert chat_log.answer_status == ChatAnswerStatus.NO_ANSWER
    assert chat_log.rewritten_query == "질문이 너무 짧습니다."
    assert db.commit_count == 2
    assert db.flush_count == 1
    assert db.rollback_count == 0


def test_answer_chat_question_raises_not_found_when_session_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    db = FakeSession()
    monkeypatch.setattr(chat_service, "get_chat_session", lambda *_args, **_kwargs: None)

    with pytest.raises(AppException) as exc_info:
        chat_service.answer_chat_question(
            db,
            ChatRequest(
                session_id="missing-session",
                question="외박 신청은 어디서 하나요?",
            ),
        )

    assert exc_info.value.error_code.code == "CHAT_SESSION_NOT_FOUND"
    assert db.commit_count == 0


def test_answer_chat_question_marks_error_when_generation_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    db = FakeSession()
    chat_session = _build_chat_session()
    chat_log = _build_chat_log()

    retrieval_calls: dict[str, object] = {}
    error_log_calls: dict[str, object] = {}

    monkeypatch.setattr(chat_service, "get_chat_session", lambda *_args, **_kwargs: chat_session)
    monkeypatch.setattr(chat_service, "create_chat_log", lambda *_args, **_kwargs: chat_log)
    monkeypatch.setattr(chat_service, "touch_chat_session_activity", lambda *_args, **_kwargs: chat_session)
    monkeypatch.setattr(chat_service, "validate_question", lambda *_args, **_kwargs: (True, "외박 신청은 어디서 하나요?"))
    monkeypatch.setattr(chat_service, "create_query_embedding", lambda *_args, **_kwargs: [0.1, 0.2, 0.3])
    monkeypatch.setattr(
        chat_service,
        "search_similar_chunks",
        lambda *_args, **_kwargs: [
            {
                "regulation_chunk_id": 1001,
                "document_id": "dorm-rule",
                "document_version": "v1",
                "chunk_id": "chunk-1",
                "content": "외박 신청은 포털에서 가능합니다.",
                "source_url": "https://example.com/rules/1",
                "similarity": 0.98,
            }
        ],
    )

    def raise_generation_error(*_args, **_kwargs):
        raise RuntimeError("llm failed")

    monkeypatch.setattr(chat_service, "generate_answer", raise_generation_error)
    monkeypatch.setattr(
        chat_service,
        "create_chat_retrieval_results",
        lambda *_args, **kwargs: retrieval_calls.update(kwargs) or [],
    )
    monkeypatch.setattr(
        chat_service,
        "mark_chat_retrieval_results_used_in_answer",
        lambda *_args, **_kwargs: pytest.fail("failed generation should not mark retrieval results used"),
    )
    monkeypatch.setattr(
        chat_service,
        "create_chat_error_log",
        lambda *_args, **kwargs: error_log_calls.update(kwargs) or object(),
    )

    with pytest.raises(RuntimeError, match="llm failed"):
        chat_service.answer_chat_question(
            db,
            ChatRequest(
                session_id="session-123",
                question="외박 신청은 어디서 하나요?",
                dormitory="제1학생생활관",
            ),
        )

    assert chat_log.answer_status == ChatAnswerStatus.ERROR
    assert chat_log.rewritten_query == "외박 신청은 어디서 하나요?"
    assert chat_log.answer == ""
    assert retrieval_calls["chat_log_id"] == 501
    assert error_log_calls["chat_log_id"] == 501
    assert error_log_calls["session_id"] == "session-123"
    assert error_log_calls["error_type"] == chat_service.ERROR_TYPE_LLM_API
    assert error_log_calls["occurred_step"] == chat_service.STEP_ANSWER_GENERATION
    assert error_log_calls["error_message"] == "llm failed"
    assert error_log_calls["error_detail"] == "RuntimeError: llm failed"
    assert db.commit_count == 2
    assert db.flush_count == 1
    assert db.rollback_count == 1


def test_answer_chat_question_raises_expired_when_session_is_inactive(monkeypatch: pytest.MonkeyPatch) -> None:
    db = FakeSession()
    expired_chat_session = _build_chat_session()
    expired_chat_session.last_activity_at = datetime(2026, 4, 27, 9, 0, 0)

    monkeypatch.setattr(chat_service, "get_chat_session", lambda *_args, **_kwargs: expired_chat_session)
    monkeypatch.setattr(chat_service, "create_chat_log", lambda *_args, **_kwargs: pytest.fail("chat_log should not be created"))
    monkeypatch.setattr(chat_service, "touch_chat_session_activity", lambda *_args, **_kwargs: pytest.fail("expired session should not be updated"))
    monkeypatch.setattr(chat_service, "get_settings", lambda: type("SettingsStub", (), {"chat_session_timeout_minutes": 30})())
    monkeypatch.setattr(chat_service, "get_current_utc_time", lambda: datetime(2026, 4, 27, 10, 0, 1))

    with pytest.raises(AppException) as exc_info:
        chat_service.answer_chat_question(
            db,
            ChatRequest(
                session_id="session-123",
                question="외박 신청은 어디서 하나요?",
            ),
        )

    assert exc_info.value.error_code.code == "CHAT_SESSION_EXPIRED"
    assert "30 minutes" in exc_info.value.detail
    assert db.commit_count == 0
    assert db.flush_count == 0


def test_flatten_grouped_retrieval_items_deduplicates_same_chunk() -> None:
    dormitory_chunks = {
        "제1학생생활관": [
            {
                "regulation_chunk_id": 16,
                "document_id": "admission_008",
                "document_version": "v1",
                "chunk_id": "chunk-a",
                "similarity": 0.429,
            },
            {
                "regulation_chunk_id": 13,
                "document_id": "admission_005",
                "document_version": "v1",
                "chunk_id": "chunk-b",
                "similarity": 0.416,
            },
        ],
        "제2학생생활관": [
            {
                "regulation_chunk_id": 16,
                "document_id": "admission_008",
                "document_version": "v1",
                "chunk_id": "chunk-a",
                "similarity": 0.429,
            },
            {
                "regulation_chunk_id": 13,
                "document_id": "admission_005",
                "document_version": "v1",
                "chunk_id": "chunk-b",
                "similarity": 0.416,
            },
        ],
    }

    result = chat_service._flatten_grouped_retrieval_items(dormitory_chunks)

    assert len(result) == 2
    assert result[0]["regulation_chunk_id"] == 16
    assert result[1]["regulation_chunk_id"] == 13


def test_assign_citation_labels_adds_sequential_labels() -> None:
    result = chat_service._assign_citation_labels(
        [
            {"regulation_chunk_id": 16, "chunk_id": "chunk-a"},
            {"regulation_chunk_id": 13, "chunk_id": "chunk-b"},
        ]
    )

    assert result[0]["citation_label"] == "C1"
    assert result[1]["citation_label"] == "C2"


def test_build_chat_error_metadata_defaults_timeout_error() -> None:
    result = chat_service._build_chat_error_metadata(TimeoutError("request timed out"))

    assert result.error_type == chat_service.ERROR_TYPE_TIMEOUT
    assert result.occurred_step is None
    assert result.error_message == "request timed out"
