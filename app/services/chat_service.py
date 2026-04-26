from datetime import datetime
from datetime import timedelta
from time import perf_counter
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.error_codes import CHAT_SESSION_EXPIRED
from app.core.error_codes import CHAT_SESSION_NOT_FOUND
from app.core.exceptions import AppException
from app.db.models.chat_enums import ChatAnswerStatus
from app.repositories.chat_log_repository import create_chat_log
from app.repositories.chat_retrieval_result_repository import create_chat_retrieval_results
from app.repositories.chat_retrieval_result_repository import mark_chat_retrieval_results_used_in_answer
from app.repositories.chat_log_repository import get_chat_session
from app.repositories.chat_log_repository import touch_chat_session_activity
from app.repositories.chat_log_repository import update_chat_log_result
from app.repositories.regulation_chunk_repository import search_similar_chunks
from app.schemas.chat import ChatRequest
from app.schemas.chat import ChatResponse
from app.services.embeddings import create_query_embedding
from app.services.generator import generate_answer
from app.services.generator import generate_grouped_answer
from app.services.validator import validate_question

ANSWER_MODEL_NAME = "gpt-4o-mini"
PROMPT_VERSION_SINGLE = "chat-answer-v1"
PROMPT_VERSION_GROUPED = "chat-answer-grouped-v1"
RETRIEVAL_VERSION_SINGLE = "dormitory-search-v1"
RETRIEVAL_VERSION_GROUPED = "dormitory-search-grouped-v1"
RETRIEVAL_METHOD_SINGLE = "vector_dormitory_top_k"
RETRIEVAL_METHOD_GROUPED = "vector_grouped_dormitory_top_k"
NO_ANSWER_MESSAGE = "관련 정보를 찾을 수 없습니다."
INVALID_QUESTION_MESSAGE = "기숙사 관련 질문을 입력해주세요."


def answer_chat_question(db: Session, payload: ChatRequest) -> ChatResponse:
    chat_session = get_chat_session(db, payload.session_id)
    if chat_session is None:
        raise AppException(CHAT_SESSION_NOT_FOUND)
    if _is_chat_session_expired(chat_session.last_activity_at):
        raise AppException(
            CHAT_SESSION_EXPIRED,
            detail=_build_chat_session_expired_message(),
        )

    chat_log = create_chat_log(
        db,
        session_id=chat_session.session_id,
        user_id=chat_session.user_id,
        question=payload.question,
    )
    touch_chat_session_activity(db, chat_session)
    db.commit()
    db.refresh(chat_log)

    started_at = perf_counter()
    normalized_question = None

    try:
        is_valid, normalized_question = validate_question(payload.question)

        if not is_valid:
            return _finalize_chat_log(
                db,
                chat_log=chat_log,
                session_id=payload.session_id,
                answer_status=ChatAnswerStatus.NO_ANSWER,
                answer=INVALID_QUESTION_MESSAGE,
                source_url="",
                rewritten_query=normalized_question,
                model_name=None,
                prompt_version=None,
                retrieval_version=None,
                response_time_ms=_elapsed_ms(started_at),
            )

        if payload.dormitory:
            return _answer_single_dormitory_chat(
                db,
                chat_log=chat_log,
                session_id=payload.session_id,
                question=normalized_question,
                dormitory=payload.dormitory,
                started_at=started_at,
            )

        return _answer_grouped_chat(
            db,
            chat_log=chat_log,
            session_id=payload.session_id,
            question=normalized_question,
            started_at=started_at,
        )
    except Exception:
        db.rollback()
        _finalize_chat_log(
            db,
            chat_log=chat_log,
            session_id=payload.session_id,
            answer_status=ChatAnswerStatus.ERROR,
            answer="",
            source_url="",
            rewritten_query=normalized_question,
            model_name=None,
            prompt_version=None,
            retrieval_version=None,
            response_time_ms=_elapsed_ms(started_at),
        )
        raise


def _answer_single_dormitory_chat(
    db: Session,
    *,
    chat_log,
    session_id: str,
    question: str,
    dormitory: str,
    started_at: float,
) -> ChatResponse:
    query_embedding = create_query_embedding(question)
    chunks = search_similar_chunks(
        db=db,
        query_embedding=query_embedding,
        dormitory=dormitory,
        top_k=3,
    )

    if not chunks:
        return _finalize_chat_log(
            db,
            chat_log=chat_log,
            session_id=session_id,
            answer_status=ChatAnswerStatus.NO_ANSWER,
            answer=NO_ANSWER_MESSAGE,
            source_url="",
            rewritten_query=question,
            model_name=None,
            prompt_version=None,
            retrieval_version=RETRIEVAL_VERSION_SINGLE,
            response_time_ms=_elapsed_ms(started_at),
        )

    create_chat_retrieval_results(
        db,
        chat_log_id=chat_log.chat_log_id,
        retrieval_items=chunks,
        retrieval_method=RETRIEVAL_METHOD_SINGLE,
    )
    answer, source_url = generate_answer(question, chunks)
    return _finalize_chat_log(
        db,
        chat_log=chat_log,
        session_id=session_id,
        answer_status=ChatAnswerStatus.SUCCESS,
        answer=answer,
        source_url=source_url or "",
        rewritten_query=question,
        model_name=ANSWER_MODEL_NAME,
        prompt_version=PROMPT_VERSION_SINGLE,
        retrieval_version=RETRIEVAL_VERSION_SINGLE,
        response_time_ms=_elapsed_ms(started_at),
        mark_retrieval_used=True,
    )


def _answer_grouped_chat(
    db: Session,
    *,
    chat_log,
    session_id: str,
    question: str,
    started_at: float,
) -> ChatResponse:
    query_embedding = create_query_embedding(question)
    dormitories = ["제1학생생활관", "제2학생생활관", "제3학생생활관"]
    dormitory_chunks: dict[str, list[dict]] = {}

    for dormitory in dormitories:
        dormitory_chunks[dormitory] = search_similar_chunks(
            db=db,
            query_embedding=query_embedding,
            dormitory=dormitory,
            top_k=2,
        )

    if not any(dormitory_chunks.values()):
        return _finalize_chat_log(
            db,
            chat_log=chat_log,
            session_id=session_id,
            answer_status=ChatAnswerStatus.NO_ANSWER,
            answer=NO_ANSWER_MESSAGE,
            source_url="",
            rewritten_query=question,
            model_name=None,
            prompt_version=None,
            retrieval_version=RETRIEVAL_VERSION_GROUPED,
            response_time_ms=_elapsed_ms(started_at),
        )

    flattened_chunks = _flatten_grouped_retrieval_items(dormitory_chunks)
    create_chat_retrieval_results(
        db,
        chat_log_id=chat_log.chat_log_id,
        retrieval_items=flattened_chunks,
        retrieval_method=RETRIEVAL_METHOD_GROUPED,
    )
    answer, source_url = generate_grouped_answer(question, dormitory_chunks)
    return _finalize_chat_log(
        db,
        chat_log=chat_log,
        session_id=session_id,
        answer_status=ChatAnswerStatus.SUCCESS,
        answer=answer,
        source_url=source_url or "",
        rewritten_query=question,
        model_name=ANSWER_MODEL_NAME,
        prompt_version=PROMPT_VERSION_GROUPED,
        retrieval_version=RETRIEVAL_VERSION_GROUPED,
        response_time_ms=_elapsed_ms(started_at),
        mark_retrieval_used=True,
    )


def _finalize_chat_log(
    db: Session,
    *,
    chat_log,
    session_id: str,
    answer_status: ChatAnswerStatus,
    answer: str,
    source_url: str,
    rewritten_query: Optional[str],
    model_name: Optional[str],
    prompt_version: Optional[str],
    retrieval_version: Optional[str],
    response_time_ms: int,
    mark_retrieval_used: bool = False,
) -> ChatResponse:
    if mark_retrieval_used:
        mark_chat_retrieval_results_used_in_answer(
            db,
            chat_log_id=chat_log.chat_log_id,
        )
    update_chat_log_result(
        db,
        chat_log,
        answer_status=answer_status,
        answer=answer,
        rewritten_query=rewritten_query,
        model_name=model_name,
        prompt_version=prompt_version,
        retrieval_version=retrieval_version,
        response_time=response_time_ms,
    )
    db.commit()
    db.refresh(chat_log)

    return ChatResponse(
        chat_log_id=chat_log.chat_log_id,
        session_id=session_id,
        answer=answer,
        answer_status=answer_status.value,
        source_url=source_url,
    )


def _elapsed_ms(started_at: float) -> int:
    return max(int((perf_counter() - started_at) * 1000), 0)


def _is_chat_session_expired(last_activity_at: datetime) -> bool:
    settings = get_settings()
    expiration_threshold = datetime.utcnow() - timedelta(minutes=settings.chat_session_timeout_minutes)
    return last_activity_at < expiration_threshold


def _build_chat_session_expired_message() -> str:
    settings = get_settings()
    return (
        f"chat session expired after {settings.chat_session_timeout_minutes} minutes of inactivity. "
        "please start a new chat session"
    )


def _flatten_grouped_retrieval_items(dormitory_chunks: dict[str, list[dict]]) -> list[dict]:
    flattened_items: list[dict] = []
    for dormitory, chunks in dormitory_chunks.items():
        for chunk in chunks:
            flattened_item = dict(chunk)
            flattened_item["retrieval_group"] = dormitory
            flattened_items.append(flattened_item)
    return flattened_items
