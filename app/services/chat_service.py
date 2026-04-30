from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from time import perf_counter
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.error_codes import CHAT_SESSION_EXPIRED
from app.core.error_codes import CHAT_LOG_NOT_FOUND
from app.core.error_codes import CHAT_SESSION_NOT_FOUND
from app.core.exceptions import AppException
from app.core.time_utils import get_current_utc_time
from app.db.models.chat_enums import ChatAnswerStatus
from app.db.session import get_session_factory
from app.repositories.chat_error_log_repository import create_chat_error_log
from app.repositories.chat_log_repository import create_chat_log
from app.repositories.chat_log_repository import get_chat_log_by_id
from app.repositories.chat_log_repository import get_chat_session
from app.repositories.chat_log_repository import touch_chat_session_activity
from app.repositories.chat_log_repository import update_chat_log_result
from app.repositories.chat_retrieval_result_repository import create_chat_retrieval_results
from app.repositories.chat_retrieval_result_repository import mark_chat_retrieval_results_used_in_answer
from app.repositories.regulation_chunk_repository import search_similar_chunks
from app.repositories.regulation_chunk_repository import search_similar_chunks_for_dormitories
from app.schemas.chat import ChatRequest
from app.schemas.chat import ChatResponse
from app.services.embeddings import create_query_embedding
from app.services.generator import generate_answer
from app.services.validator import validate_question


from app.repositories.regulation_chunk_repository import search_similar_chunks_all_dormitories

ERROR_TYPE_TIMEOUT = "TIMEOUT"
ERROR_TYPE_LLM_API = "LLM_API_ERROR"
ERROR_TYPE_RETRIEVAL = "RETRIEVAL_ERROR"
ERROR_TYPE_PROMPT_BUILD = "PROMPT_BUILD_ERROR"
ERROR_TYPE_VALIDATION = "VALIDATION_ERROR"
ERROR_TYPE_UNKNOWN = "UNKNOWN_ERROR"

STEP_QUESTION_VALIDATION = "QUESTION_VALIDATION"
STEP_QUERY_REWRITE = "QUERY_REWRITE"
STEP_RETRIEVAL = "RETRIEVAL"
STEP_RERANK = "RERANK"
STEP_ANSWER_GENERATION = "ANSWER_GENERATION"
STEP_RESPONSE_RENDERING = "RESPONSE_RENDERING"


@dataclass(frozen=True)
class ChatErrorMetadata:
    error_type: str
    occurred_step: Optional[str]
    error_message: str
    error_detail: Optional[str]


def answer_chat_question(db: Session, payload: ChatRequest) -> ChatResponse:
    settings = get_settings()
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
    chat_log_id = chat_log.chat_log_id

    try:
        try:
            is_valid, normalized_question = validate_question(payload.question)
        except Exception as exc:
            _attach_chat_error_metadata(
                exc,
                error_type=ERROR_TYPE_VALIDATION,
                occurred_step=STEP_QUESTION_VALIDATION,
            )
            raise

        if not is_valid:
            return _finalize_chat_log(
                db,
                chat_log_id=chat_log_id,
                session_id=payload.session_id,
                answer_status=ChatAnswerStatus.NO_ANSWER,
                answer=settings.chat_invalid_question_message,
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
                chat_log_id=chat_log_id,
                session_id=payload.session_id,
                question=normalized_question,
                dormitory=payload.dormitory,
                started_at=started_at,
            )

        return _answer_unspecified_dormitory_chat(
            db,
            chat_log_id=chat_log_id,
            session_id=payload.session_id,
            question=normalized_question,
            started_at=started_at,
        )
    except Exception as exc:
        error_metadata = _build_chat_error_metadata(exc)
        db.rollback()
        _finalize_chat_log_in_new_session(
            chat_log_id=chat_log_id,
            session_id=payload.session_id,
            answer_status=ChatAnswerStatus.ERROR,
            answer="",
            source_url="",
            rewritten_query=normalized_question,
            model_name=None,
            prompt_version=None,
            retrieval_version=None,
            response_time_ms=_elapsed_ms(started_at),
            error_metadata=error_metadata,
        )
        raise


def _answer_single_dormitory_chat(
    db: Session,
    *,
    chat_log_id: int,
    session_id: str,
    question: str,
    dormitory: str,
    started_at: float,
) -> ChatResponse:
    settings = get_settings()

    retrieval_method = settings.chat_retrieval_method_single
    retrieval_version = settings.chat_retrieval_version_single

    try:
        query_embedding = create_query_embedding(question)

        chunks = search_similar_chunks(
            db=db,
            query_embedding=query_embedding,
            dormitory=dormitory,
            top_k=settings.chat_single_dormitory_top_k,
        )

        # 1차 검색 결과가 없거나 유사도가 낮으면 전체 생활관 fallback 검색
        if _should_fallback_retrieval(chunks):
            chunks = search_similar_chunks_all_dormitories(
                db=db,
                query_embedding=query_embedding,
                top_k=settings.chat_fallback_top_k,
            )
            retrieval_method = settings.chat_retrieval_method_fallback
            retrieval_version = settings.chat_retrieval_version_fallback

    except Exception as exc:
        _attach_chat_error_metadata(
            exc,
            error_type=ERROR_TYPE_RETRIEVAL,
            occurred_step=STEP_RETRIEVAL,
        )
        raise

    if not chunks:
        return _finalize_chat_log(
            db,
            chat_log_id=chat_log_id,
            session_id=session_id,
            answer_status=ChatAnswerStatus.NO_ANSWER,
            answer=settings.chat_no_answer_message,
            source_url="",
            rewritten_query=question,
            model_name=None,
            prompt_version=None,
            retrieval_version=retrieval_version,
            response_time_ms=_elapsed_ms(started_at),
        )

    try:
        # 먼저 현재 검색 결과로 답변 생성
        answer_result = generate_answer(
            question,
            chunks,
            dormitory=dormitory,
            is_fallback=retrieval_method == settings.chat_retrieval_method_fallback,
        )

        # 검색 결과는 있었지만 답변 생성기가 "관련 정보를 찾을 수 없습니다."라고 한 경우
        # 아직 fallback 검색을 하지 않은 상태라면 전체 생활관 검색으로 한 번 더 시도
        if (
            answer_result.answer.strip() == settings.chat_no_answer_message
            and retrieval_method != settings.chat_retrieval_method_fallback
        ):
            fallback_chunks = search_similar_chunks_all_dormitories(
                db=db,
                query_embedding=query_embedding,
                top_k=settings.chat_fallback_top_k,
            )

            if fallback_chunks:
                chunks = fallback_chunks
                retrieval_method = settings.chat_retrieval_method_fallback
                retrieval_version = settings.chat_retrieval_version_fallback

                answer_result = generate_answer(
                    question,
                    chunks,
                    dormitory=dormitory,
                    is_fallback=True,
                )

    except Exception as exc:
        _attach_chat_error_metadata(
            exc,
            error_type=ERROR_TYPE_LLM_API,
            occurred_step=STEP_ANSWER_GENERATION,
        )
        raise

    # 최종적으로 사용된 chunks만 chat_retrieval_result에 저장
    # fallback이 발생했다면 fallback chunks가 저장됨
    try:
        create_chat_retrieval_results(
            db,
            chat_log_id=chat_log_id,
            retrieval_items=chunks,
            retrieval_method=retrieval_method,
        )
    except Exception as exc:
        _attach_chat_error_metadata(
            exc,
            error_type=ERROR_TYPE_RETRIEVAL,
            occurred_step=STEP_RETRIEVAL,
        )
        raise

    db.commit()
    db.close()

    return _finalize_chat_log_in_new_session(
        chat_log_id=chat_log_id,
        session_id=session_id,
        answer_status=ChatAnswerStatus.SUCCESS,
        answer=answer_result.answer,
        source_url=answer_result.source_url or "",
        rewritten_query=question,
        model_name=settings.chat_answer_model,
        prompt_version=settings.chat_prompt_version_single,
        retrieval_version=retrieval_version,
        response_time_ms=_elapsed_ms(started_at),
        mark_retrieval_used=True,
        cited_regulation_chunk_ids=answer_result.cited_regulation_chunk_ids,
    )

def _answer_unspecified_dormitory_chat(
    db: Session,
    *,
    chat_log_id: int,
    session_id: str,
    question: str,
    started_at: float,
) -> ChatResponse:
    settings = get_settings()
    try:
        query_embedding = create_query_embedding(question)
    except Exception as exc:
        _attach_chat_error_metadata(
            exc,
            error_type=ERROR_TYPE_RETRIEVAL,
            occurred_step=STEP_RETRIEVAL,
        )
        raise
    try:
        chunks = search_similar_chunks_for_dormitories(
            db=db,
            query_embedding=query_embedding,
            dormitories=settings.chat_grouped_dormitories,
            top_k=settings.chat_grouped_dormitory_top_k,
        )
    except Exception as exc:
        _attach_chat_error_metadata(
            exc,
            error_type=ERROR_TYPE_RETRIEVAL,
            occurred_step=STEP_RETRIEVAL,
        )
        raise

    if not chunks:
        return _finalize_chat_log(
            db,
            chat_log_id=chat_log_id,
            session_id=session_id,
            answer_status=ChatAnswerStatus.NO_ANSWER,
            answer=settings.chat_no_answer_message,
            source_url="",
            rewritten_query=question,
            model_name=None,
            prompt_version=None,
            retrieval_version=settings.chat_retrieval_version_grouped,
            response_time_ms=_elapsed_ms(started_at),
        )

    try:
        create_chat_retrieval_results(
            db,
            chat_log_id=chat_log_id,
            retrieval_items=chunks,
            retrieval_method=settings.chat_retrieval_method_grouped,
        )
    except Exception as exc:
        _attach_chat_error_metadata(
            exc,
            error_type=ERROR_TYPE_RETRIEVAL,
            occurred_step=STEP_RETRIEVAL,
        )
        raise
    db.commit()
    try:
        answer_result = generate_answer(question, chunks)
    except Exception as exc:
        _attach_chat_error_metadata(
            exc,
            error_type=ERROR_TYPE_LLM_API,
            occurred_step=STEP_ANSWER_GENERATION,
        )
        raise
    db.close()
    return _finalize_chat_log_in_new_session(
        chat_log_id=chat_log_id,
        session_id=session_id,
        answer_status=ChatAnswerStatus.SUCCESS,
        answer=answer_result.answer,
        source_url=answer_result.source_url or "",
        rewritten_query=question,
        model_name=settings.chat_answer_model,
        prompt_version=settings.chat_prompt_version_grouped,
        retrieval_version=settings.chat_retrieval_version_grouped,
        response_time_ms=_elapsed_ms(started_at),
        mark_retrieval_used=True,
        cited_regulation_chunk_ids=answer_result.cited_regulation_chunk_ids,
    )


def _finalize_chat_log(
    db: Session,
    *,
    chat_log_id: int,
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
    cited_regulation_chunk_ids: Optional[list[int]] = None,
    error_metadata: Optional[ChatErrorMetadata] = None,
) -> ChatResponse:
    chat_log = get_chat_log_by_id(db, chat_log_id)
    if chat_log is None:
        raise AppException(CHAT_LOG_NOT_FOUND)

    if mark_retrieval_used:
        try:
            mark_chat_retrieval_results_used_in_answer(
                db,
                chat_log_id=chat_log_id,
                cited_regulation_chunk_ids=cited_regulation_chunk_ids or [],
            )
        except Exception as exc:
            _attach_chat_error_metadata(
                exc,
                error_type=ERROR_TYPE_PROMPT_BUILD,
                occurred_step=STEP_RESPONSE_RENDERING,
            )
            raise
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
    if error_metadata is not None:
        create_chat_error_log(
            db,
            chat_log_id=chat_log_id,
            session_id=session_id,
            error_type=error_metadata.error_type,
            error_message=error_metadata.error_message,
            error_detail=error_metadata.error_detail,
            occurred_step=error_metadata.occurred_step,
        )
    db.commit()
    db.refresh(chat_log)

    return ChatResponse(
        chat_log_id=chat_log_id,
        session_id=session_id,
        answer=answer,
        answer_status=answer_status.value,
        source_url=source_url,
    )


def _finalize_chat_log_in_new_session(
    *,
    chat_log_id: int,
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
    cited_regulation_chunk_ids: Optional[list[int]] = None,
    error_metadata: Optional[ChatErrorMetadata] = None,
) -> ChatResponse:
    session_factory = get_session_factory()
    finalize_db = session_factory()
    try:
        return _finalize_chat_log(
            finalize_db,
            chat_log_id=chat_log_id,
            session_id=session_id,
            answer_status=answer_status,
            answer=answer,
            source_url=source_url,
            rewritten_query=rewritten_query,
            model_name=model_name,
            prompt_version=prompt_version,
            retrieval_version=retrieval_version,
            response_time_ms=response_time_ms,
            mark_retrieval_used=mark_retrieval_used,
            cited_regulation_chunk_ids=cited_regulation_chunk_ids,
            error_metadata=error_metadata,
        )
    finally:
        finalize_db.close()


def _elapsed_ms(started_at: float) -> int:
    return max(int((perf_counter() - started_at) * 1000), 0)


def _is_chat_session_expired(last_activity_at: datetime) -> bool:
    settings = get_settings()
    expiration_threshold = get_current_utc_time() - timedelta(minutes=settings.chat_session_timeout_minutes)
    return last_activity_at < expiration_threshold


def _build_chat_session_expired_message() -> str:
    settings = get_settings()
    return (
        f"chat session expired after {settings.chat_session_timeout_minutes} minutes of inactivity. "
        "please start a new chat session"
    )


def _attach_chat_error_metadata(
    exc: Exception,
    *,
    error_type: str,
    occurred_step: Optional[str],
) -> None:
    setattr(exc, "_chat_error_type", error_type)
    setattr(exc, "_chat_occurred_step", occurred_step)


def _build_chat_error_metadata(exc: Exception) -> ChatErrorMetadata:
    error_type = getattr(exc, "_chat_error_type", None)
    occurred_step = getattr(exc, "_chat_occurred_step", None)

    if error_type is None:
        if isinstance(exc, TimeoutError):
            error_type = ERROR_TYPE_TIMEOUT
        else:
            error_type = ERROR_TYPE_UNKNOWN

    error_message = str(exc).strip() or type(exc).__name__
    error_detail = f"{type(exc).__name__}: {error_message}"

    return ChatErrorMetadata(
        error_type=error_type,
        occurred_step=occurred_step,
        error_message=error_message,
        error_detail=error_detail,
    )


def _should_fallback_retrieval(chunks: list[dict]) -> bool:
    settings = get_settings()

    if not chunks:
        return True

    top_similarity = chunks[0].get("similarity")
    if top_similarity is None:
        return True

    return float(top_similarity) < settings.chat_fallback_similarity_threshold
