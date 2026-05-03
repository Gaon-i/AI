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
from app.repositories.regulation_chunk_repository import search_hybrid_chunks
from app.repositories.regulation_chunk_repository import search_hybrid_chunks_all_dormitories
from app.repositories.regulation_chunk_repository import search_hybrid_chunks_for_dormitories
from app.schemas.chat import ChatRequest
from app.schemas.chat import ChatResponse
from app.services.embeddings import create_query_embedding
from app.services.generator import generate_answer
from app.services.validator import validate_question
from app.services.query_rewriter import expand_query_for_retrieval


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
    rewritten_query = question

    try:
        retrieval_query = question

        if _should_pre_expand_query(question):
            retrieval_query = expand_query_for_retrieval(
                question=question,
                dormitory=dormitory,
            )
            rewritten_query = retrieval_query

        query_embedding = create_query_embedding(retrieval_query)

        chunks = search_hybrid_chunks(
            db=db,
            query_text=retrieval_query,
            query_embedding=query_embedding,
            dormitory=dormitory,
            top_k=settings.chat_single_dormitory_top_k,
            candidate_k=20,
            keyword_weight=0.3,
        )

        # 1차 검색 결과가 없거나 유사도가 낮으면 전체 생활관 fallback 검색
        if _should_fallback_retrieval(chunks):
            chunks = search_hybrid_chunks_all_dormitories(
                db=db,
                query_text=retrieval_query,
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
            _is_no_answer(answer_result.answer)
            and retrieval_method != settings.chat_retrieval_method_fallback
        ):
            fallback_chunks = search_hybrid_chunks_all_dormitories(
                db=db,
                query_text=retrieval_query,
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
                
        
        # 전체 생활관 fallback까지 했는데도 답변을 못 만들면
        # LLM query expansion으로 검색용 질의를 확장한 뒤 재검색
        if _is_no_answer(answer_result.answer):
            expanded_query = expand_query_for_retrieval(
                question=question,
                dormitory=dormitory,
            )

            if expanded_query != question:
                expanded_query_embedding = create_query_embedding(expanded_query)
                rewritten_query = expanded_query

                # 1차: 확장 query로 사용자 dormitory + 공통 문서 검색
                expanded_chunks = search_hybrid_chunks(
                    db=db,
                    query_text=expanded_query,
                    query_embedding=expanded_query_embedding,
                    dormitory=dormitory,
                    top_k=settings.chat_single_dormitory_top_k,
                )


                if expanded_chunks:
                    chunks = expanded_chunks
                    retrieval_method = settings.chat_retrieval_method_query_expansion
                    retrieval_version = settings.chat_retrieval_version_query_expansion

                    answer_result = generate_answer(
                        question,
                        chunks,
                        dormitory=dormitory,
                        is_fallback=False,
                    )

                # 중요:
                # 확장 query + 사용자 dormitory 검색으로도 답변이 부족하면
                # 확장 query + 전체 생활관 검색을 반드시 한 번 더 수행
                if _is_no_answer(answer_result.answer):
                    expanded_all_chunks = search_hybrid_chunks_all_dormitories(
                        db=db,
                        query_text=expanded_query,
                        query_embedding=expanded_query_embedding,
                        top_k=settings.chat_fallback_top_k,
                    )

                    if expanded_all_chunks:
                        chunks = expanded_all_chunks
                        retrieval_method = settings.chat_retrieval_method_query_expansion
                        retrieval_version = settings.chat_retrieval_version_query_expansion

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

    final_answer_status = ChatAnswerStatus.SUCCESS
    final_source_url = answer_result.source_url or ""

    if _is_no_answer(answer_result.answer):
        final_answer_status = ChatAnswerStatus.NO_ANSWER
        final_source_url = ""

    

    return _finalize_chat_log_in_new_session(
        chat_log_id=chat_log_id,
        session_id=session_id,
        answer_status=final_answer_status,
        answer=answer_result.answer,
        source_url=final_source_url,
        rewritten_query=rewritten_query,
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
    retrieval_method = settings.chat_retrieval_method_grouped
    retrieval_version = settings.chat_retrieval_version_grouped
    rewritten_query = question

    try:
        retrieval_query = question

        if _should_pre_expand_query(question):
            retrieval_query = expand_query_for_retrieval(
                question=question,
                dormitory=None,
            )
        rewritten_query = retrieval_query

        query_embedding = create_query_embedding(retrieval_query)
    except Exception as exc:
        _attach_chat_error_metadata(
            exc,
            error_type=ERROR_TYPE_RETRIEVAL,
            occurred_step=STEP_RETRIEVAL,
        )
        raise

    try:
        chunks = search_hybrid_chunks_for_dormitories(
            db=db,
            query_text=retrieval_query,
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
            rewritten_query=rewritten_query,
            model_name=None,
            prompt_version=None,
            retrieval_version=retrieval_version,
            response_time_ms=_elapsed_ms(started_at),
        )

    try:
        answer_result = generate_answer(question, chunks)

        # 비로그인/생활관 미지정 상태에서 원문 검색으로 답변을 못 만들면
        # query expansion으로 검색용 질의를 확장한 뒤 전체 생활관 대상으로 재검색
        if _is_no_answer(answer_result.answer):
            expanded_query = expand_query_for_retrieval(
                question=question,
                dormitory=None,
            )

            if expanded_query != question:
                expanded_query_embedding = create_query_embedding(expanded_query)
                rewritten_query = expanded_query

                expanded_chunks = search_hybrid_chunks_for_dormitories(
                    db=db,
                    query_text=expanded_query,
                    query_embedding=expanded_query_embedding,
                    dormitories=settings.chat_grouped_dormitories,
                    top_k=settings.chat_fallback_top_k,
                )

                rerank_keywords = _get_query_expansion_rerank_keywords(
                    question,
                    expanded_query,
                )
                expanded_chunks = _rerank_chunks_by_keywords(
                    expanded_chunks,
                    rerank_keywords,
                )
                

                if expanded_chunks:
                    chunks = expanded_chunks
                    retrieval_method = settings.chat_retrieval_method_query_expansion
                    retrieval_version = settings.chat_retrieval_version_query_expansion

                    answer_result = generate_answer(
                        question,
                        chunks,
                    )

    except Exception as exc:
        _attach_chat_error_metadata(
            exc,
            error_type=ERROR_TYPE_LLM_API,
            occurred_step=STEP_ANSWER_GENERATION,
        )
        raise

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

    final_answer_status = ChatAnswerStatus.SUCCESS
    final_source_url = answer_result.source_url or ""

    if _is_no_answer(answer_result.answer):
        final_answer_status = ChatAnswerStatus.NO_ANSWER
        final_source_url = ""

    return _finalize_chat_log_in_new_session(
        chat_log_id=chat_log_id,
        session_id=session_id,
        answer_status=final_answer_status,
        answer=answer_result.answer,
        source_url=final_source_url,
        rewritten_query=rewritten_query,
        model_name=settings.chat_answer_model,
        prompt_version=settings.chat_prompt_version_grouped,
        retrieval_version=retrieval_version,
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

    top_vector_score = chunks[0].get("vector_score")
    if top_vector_score is None:
        top_vector_score = chunks[0].get("vector_similarity")
    if top_vector_score is None:
        top_vector_score = chunks[0].get("similarity")
    if top_vector_score is None:
        return True

    return float(top_vector_score) < settings.chat_fallback_similarity_threshold

def _is_no_answer(answer: str) -> bool:
    settings = get_settings()
    return settings.chat_no_answer_message in answer.strip()

def _get_query_expansion_rerank_keywords(question: str, expanded_query: str) -> list[str]:
    text = f"{question} {expanded_query}".replace(" ", "")

    cooking_triggers = [
    "라면끓",
    "끓여먹",
    "끓여",
    "취사",
    "조리",
    "요리",
    "해먹",
    "해먹어",
    "해먹어도",
    "음식해",
    "음식해먹",
    "전기포트",
    "라면포트",
    "에어프라이어",
    "커피포트",
    ]

    if any(trigger in text for trigger in cooking_triggers):
        return [
            "반입금지 물품",
            "반입금지",
            "취사행위",
            "취사",
            "전열기구",
            "전열기기",
            "라면포트",
            "전기포트",
            "에어프라이어",
            "커피포트",
            "화재위험",
        ]

    return []


def _rerank_chunks_by_keywords(
    chunks: list[dict],
    keywords: list[str],
) -> list[dict]:
    if not chunks or not keywords:
        return chunks

    def keyword_score(chunk: dict) -> int:
        content = (chunk.get("content") or "").lower()
        return sum(1 for keyword in keywords if keyword.lower() in content)

    return sorted(
        chunks,
        key=lambda chunk: (
            keyword_score(chunk),
            float(chunk.get("similarity") or 0.0),
        ),
        reverse=True,
    )


def _should_pre_expand_query(question: str) -> bool:
    compact_question = question.replace(" ", "")

    curfew_triggers = [
        "통금",
        "몇시까지들어",
        "몇시까지입실",
        "언제까지들어",
        "새벽에들어",
        "새벽에도들어",
        "새벽2시에들어",
        "새벽1시에들어",
        "들어가도돼",
        "출입가능",
        "문닫",
        "문열",
        "폐문",
        "개문",
    ]

    if (
        any(trigger in compact_question for trigger in curfew_triggers)
        and "휴게실" not in compact_question
    ):
        return True

    eating_place_triggers = [
        "먹을만한곳",
        "먹을거",
        "먹을것",
        "뭐먹을",
        "간단하게먹",
        "식사해결",
        "사먹을곳",
    ]

    if any(trigger in compact_question for trigger in eating_place_triggers):
        return True

    microwave_triggers = [
        "전자레인지",
        "전자렌지",
        "음식데워",
        "데워먹",
        "데워먹을",
    ]

    if any(trigger in compact_question for trigger in microwave_triggers):
        return True

    atm_triggers = [
        "atm",
        "atm기",
        "에이티엠",
        "현금인출",
        "현금뽑",
        "은행",
        "자동화기기",
        "현금자동입출금기",
    ]

    if any(trigger in compact_question.lower() for trigger in atm_triggers):
        return True

    dormitory_alias_triggers = [
        "1긱",
        "2긱",
        "3긱",
    ]

    if any(trigger in compact_question for trigger in dormitory_alias_triggers):
        return True

    cooking_triggers = [
        "라면끓",
        "라면먹",
        "끓여먹",
        "끓여",
        "방에서라면",
        "취사",
        "조리",
        "요리",
        "해먹",
        "해먹어",
        "해먹어도",
        "음식해",
        "음식해먹",
        "전기포트",
        "라면포트",
        "에어프라이어",
        "커피포트",
    ]

    if any(trigger in compact_question for trigger in cooking_triggers):
        return True

    return False
