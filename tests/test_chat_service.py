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
        self.close_count = 0
        self.refreshed_objects: list[object] = []

    def commit(self) -> None:
        self.commit_count += 1

    def flush(self) -> None:
        self.flush_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1

    def refresh(self, value) -> None:
        self.refreshed_objects.append(value)

    def close(self) -> None:
        self.close_count += 1


def _build_chat_session():
    return type(
        "ChatSessionStub",
        (),
        {
            "session_id": "session-123",
            "user_id": 7,
            "total_turns": 0,
            "last_activity_at": datetime(2026, 4, 29, 10, 0, 0),
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
    finalize_db = FakeSession()
    chat_session = _build_chat_session()
    chat_log = _build_chat_log()

    retrieval_calls: dict[str, object] = {}

    monkeypatch.setattr(chat_service, "get_chat_session", lambda *_args, **_kwargs: chat_session)
    monkeypatch.setattr(chat_service, "create_chat_log", lambda *_args, **_kwargs: chat_log)
    monkeypatch.setattr(chat_service, "get_chat_log_by_id", lambda *_args, **_kwargs: chat_log)
    monkeypatch.setattr(chat_service, "touch_chat_session_activity", lambda *_args, **_kwargs: chat_session)
    monkeypatch.setattr(chat_service, "get_session_factory", lambda: (lambda: finalize_db))
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
                "source": "생활관 규정집",
                "source_url": "https://example.com/rules/1",
                "similarity": 0.98,
            }
        ],
    )
    monkeypatch.setattr(
        chat_service,
        "generate_answer",
        lambda *_args, **_kwargs: AnswerGenerationResult(
            answer="포털에서 외박 신청을 하면 됩니다.\n\n출처: 생활관 규정집 (https://example.com/rules/1)",
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

    settings = chat_service.get_settings()
    assert response.chat_log_id == 501
    assert response.session_id == "session-123"
    assert response.answer == "포털에서 외박 신청을 하면 됩니다.\n\n출처: 생활관 규정집 (https://example.com/rules/1)"
    assert response.answer_status == "SUCCESS"
    assert response.source_url == "https://example.com/rules/1"
    assert chat_log.answer_status == ChatAnswerStatus.SUCCESS
    assert chat_log.rewritten_query == "외박 신청은 어디서 하나요?"
    assert chat_log.model_name == settings.chat_answer_model
    assert chat_log.prompt_version == settings.chat_prompt_version_single
    assert chat_log.retrieval_version == settings.chat_retrieval_version_single
    assert retrieval_calls["chat_log_id"] == 501
    assert retrieval_calls["retrieval_method"] == settings.chat_retrieval_method_single
    assert retrieval_calls["retrieval_items"][0]["regulation_chunk_id"] == 1001
    assert "citation_label" not in retrieval_calls["retrieval_items"][0]
    assert retrieval_calls["mark_used_chat_log_id"] == 501
    assert retrieval_calls["cited_regulation_chunk_ids"] == [1001]
    assert db.commit_count == 2
    assert db.close_count == 1
    assert finalize_db.commit_count == 1
    assert db.flush_count == 0
    assert finalize_db.flush_count == 1
    assert db.rollback_count == 0


def test_answer_chat_question_uses_top_scored_chunks_when_dormitory_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = FakeSession()
    finalize_db = FakeSession()
    chat_session = _build_chat_session()
    chat_log = _build_chat_log()

    retrieval_calls: dict[str, object] = {}
    generated_chunks: list[dict] = []
    multi_search_calls: list[dict] = []

    monkeypatch.setattr(chat_service, "get_chat_session", lambda *_args, **_kwargs: chat_session)
    monkeypatch.setattr(chat_service, "create_chat_log", lambda *_args, **_kwargs: chat_log)
    monkeypatch.setattr(chat_service, "get_chat_log_by_id", lambda *_args, **_kwargs: chat_log)
    monkeypatch.setattr(chat_service, "touch_chat_session_activity", lambda *_args, **_kwargs: chat_session)
    monkeypatch.setattr(chat_service, "get_session_factory", lambda: (lambda: finalize_db))
    monkeypatch.setattr(chat_service, "validate_question", lambda *_args, **_kwargs: (True, "택배는 어디서 받나요?"))
    monkeypatch.setattr(chat_service, "create_query_embedding", lambda *_args, **_kwargs: [0.1, 0.2, 0.3])

    def fake_search_similar_chunks_for_dormitories(*_args, **kwargs):
        multi_search_calls.append(kwargs)
        return [
            {
                "regulation_chunk_id": 1002,
                "document_id": "parcel-2",
                "document_version": "v1",
                "chunk_id": "chunk-2",
                "content": "생활관: 제2학생생활관\n본문: 택배는 2관 택배실에서 받습니다.",
                "source": "실제 기숙사 거주생들의 팁",
                "source_url": "https://example.com/rules/2",
                "similarity": 0.94,
                "retrieval_group": "제2학생생활관",
            },
            {
                "regulation_chunk_id": 1001,
                "document_id": "parcel-1",
                "document_version": "v1",
                "chunk_id": "chunk-1",
                "content": "생활관: 제1학생생활관\n본문: 택배는 1관 행정실에서 받습니다.",
                "source": "실제 기숙사 거주생들의 팁",
                "source_url": "https://example.com/rules/1",
                "similarity": 0.72,
                "retrieval_group": "제1학생생활관",
            },
        ]

    def fake_generate_answer(_question, chunks):
        generated_chunks.extend(chunks)
        return AnswerGenerationResult(
            answer="제2학생생활관 기준으로 택배는 택배실에서 받습니다.\n\n출처: 실제 기숙사 거주생들의 팁 (https://example.com/rules/2)",
            source_url="https://example.com/rules/2",
            cited_regulation_chunk_ids=[1002],
        )

    monkeypatch.setattr(
        chat_service,
        "search_similar_chunks",
        lambda *_args, **_kwargs: pytest.fail("unspecified dormitory should use a single multi-dormitory query"),
    )
    monkeypatch.setattr(
        chat_service,
        "search_similar_chunks_for_dormitories",
        fake_search_similar_chunks_for_dormitories,
    )
    monkeypatch.setattr(chat_service, "generate_answer", fake_generate_answer)
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
            question="택배는 어디서 받나요?",
        ),
    )

    settings = chat_service.get_settings()
    assert len(multi_search_calls) == 1
    assert multi_search_calls[0]["dormitories"] == settings.chat_grouped_dormitories
    assert multi_search_calls[0]["top_k"] == settings.chat_grouped_dormitory_top_k
    assert generated_chunks[0]["regulation_chunk_id"] == 1002
    assert generated_chunks[1]["regulation_chunk_id"] == 1001
    assert "citation_label" not in generated_chunks[0]
    assert "citation_label" not in generated_chunks[1]
    assert retrieval_calls["retrieval_method"] == settings.chat_retrieval_method_grouped
    assert retrieval_calls["retrieval_items"][0]["regulation_chunk_id"] == 1002
    assert retrieval_calls["retrieval_items"][1]["regulation_chunk_id"] == 1001
    assert retrieval_calls["cited_regulation_chunk_ids"] == [1002]
    assert response.answer == "제2학생생활관 기준으로 택배는 택배실에서 받습니다.\n\n출처: 실제 기숙사 거주생들의 팁 (https://example.com/rules/2)"
    assert response.source_url == "https://example.com/rules/2"
    assert chat_log.prompt_version == settings.chat_prompt_version_grouped
    assert chat_log.retrieval_version == settings.chat_retrieval_version_grouped


def test_answer_chat_question_returns_no_answer_for_invalid_question(monkeypatch: pytest.MonkeyPatch) -> None:
    db = FakeSession()
    chat_session = _build_chat_session()
    chat_log = _build_chat_log()

    monkeypatch.setattr(chat_service, "get_chat_session", lambda *_args, **_kwargs: chat_session)
    monkeypatch.setattr(chat_service, "create_chat_log", lambda *_args, **_kwargs: chat_log)
    monkeypatch.setattr(chat_service, "get_chat_log_by_id", lambda *_args, **_kwargs: chat_log)
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

    assert response.answer == chat_service.get_settings().chat_invalid_question_message
    assert response.answer_status == "NO_ANSWER"
    assert response.source_url == ""
    assert chat_log.answer_status == ChatAnswerStatus.NO_ANSWER
    assert chat_log.rewritten_query == "질문이 너무 짧습니다."
    assert db.commit_count == 2
    assert db.close_count == 0
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
    finalize_db = FakeSession()
    chat_session = _build_chat_session()
    chat_log = _build_chat_log()

    retrieval_calls: dict[str, object] = {}
    error_log_calls: dict[str, object] = {}

    monkeypatch.setattr(chat_service, "get_chat_session", lambda *_args, **_kwargs: chat_session)
    monkeypatch.setattr(chat_service, "create_chat_log", lambda *_args, **_kwargs: chat_log)
    monkeypatch.setattr(chat_service, "get_chat_log_by_id", lambda *_args, **_kwargs: chat_log)
    monkeypatch.setattr(chat_service, "touch_chat_session_activity", lambda *_args, **_kwargs: chat_session)
    monkeypatch.setattr(chat_service, "get_session_factory", lambda: (lambda: finalize_db))
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
                    "source": "생활관 규정집",
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
    assert db.close_count == 0
    assert finalize_db.commit_count == 1
    assert db.flush_count == 0
    assert finalize_db.flush_count == 1
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


def test_build_chat_error_metadata_defaults_timeout_error() -> None:
    result = chat_service._build_chat_error_metadata(TimeoutError("request timed out"))

    assert result.error_type == chat_service.ERROR_TYPE_TIMEOUT
    assert result.occurred_step is None
    assert result.error_message == "request timed out"
