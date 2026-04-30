from datetime import date
from datetime import datetime
from datetime import timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.error_codes import CHAT_LOG_NOT_FOUND
from app.core.exceptions import AppException
from app.core.time_utils import get_current_utc_time
from app.repositories.admin_chat_repository import get_chat_log_by_id
from app.repositories.admin_chat_repository import count_chat_review_queue_items
from app.repositories.admin_chat_repository import count_chat_sessions_by_started_date
from app.repositories.admin_chat_repository import list_chat_error_logs_by_chat_log_id
from app.repositories.admin_chat_repository import list_chat_feedbacks_by_chat_log_id
from app.repositories.admin_chat_repository import list_chat_admin_reviews_by_chat_log_id
from app.repositories.admin_chat_repository import list_chat_retrieval_results_by_chat_log_id
from app.repositories.admin_chat_repository import list_chat_review_queue_items
from app.repositories.admin_chat_repository import list_chat_sessions_by_started_date
from app.repositories.admin_chat_repository import save_chat_admin_review
from app.schemas.admin_chat import AdminChatReviewQueueReason
from app.schemas.admin_chat import AdminChatReviewQueueResult
from app.schemas.admin_chat import AdminChatReviewQueueItem
from app.schemas.admin_chat import AdminChatErrorLog
from app.schemas.admin_chat import AdminChatFeedback
from app.schemas.admin_chat import AdminChatAdminReview
from app.schemas.admin_chat import AdminChatReviewSaveRequest
from app.schemas.admin_chat import AdminChatSessionsByDateResult
from app.schemas.admin_chat import AdminChatLogDetail
from app.schemas.admin_chat import AdminChatRetrievalResult
from app.schemas.admin_chat import AdminChatSessionSummary

ANSWER_PREVIEW_MAX_LENGTH = 160


def get_admin_chat_log_detail(db: Session, chat_log_id: int) -> AdminChatLogDetail:
    chat_log = get_chat_log_by_id(db, chat_log_id)
    if chat_log is None:
        raise AppException(CHAT_LOG_NOT_FOUND)
    retrieval_results = list_chat_retrieval_results_by_chat_log_id(db, chat_log_id)
    error_logs = list_chat_error_logs_by_chat_log_id(db, chat_log_id)
    feedbacks = list_chat_feedbacks_by_chat_log_id(db, chat_log_id)
    admin_reviews = list_chat_admin_reviews_by_chat_log_id(db, chat_log_id)

    return AdminChatLogDetail(
        chat_log_id=chat_log.chat_log_id,
        session_id=chat_log.session_id,
        user_id=chat_log.user_id,
        question=chat_log.question,
        rewritten_query=chat_log.rewritten_query,
        answer=chat_log.answer,
        answer_status=chat_log.answer_status.value,
        model_name=chat_log.model_name,
        prompt_version=chat_log.prompt_version,
        retrieval_version=chat_log.retrieval_version,
        response_time=chat_log.response_time,
        created_at=chat_log.created_at,
        retrieval_results=[
            AdminChatRetrievalResult(
                chat_retrieval_result_id=item.chat_retrieval_result_id,
                regulation_chunk_id=item.regulation_chunk_id,
                document_id=item.document_id,
                document_version=item.document_version,
                chunk_id=item.chunk_id,
                retrieval_rank=item.retrieval_rank,
                retrieval_score=float(item.retrieval_score) if item.retrieval_score is not None else None,
                rerank_score=float(item.rerank_score) if item.rerank_score is not None else None,
                retrieval_method=item.retrieval_method,
                used_in_answer=item.used_in_answer,
                selected_as_citation=item.selected_as_citation,
                citation_order=item.citation_order,
                created_at=item.created_at,
            )
            for item in retrieval_results
        ],
        error_logs=[
            AdminChatErrorLog(
                error_id=item.error_id,
                error_type=item.error_type,
                error_message=item.error_message,
                error_detail=item.error_detail,
                occurred_step=item.occurred_step,
                created_at=item.created_at,
            )
            for item in error_logs
        ],
        feedbacks=[
            AdminChatFeedback(
                feedback_id=item.feedback_id,
                user_id=item.user_id,
                feedback_type=item.feedback_type,
                is_helpful=item.is_helpful,
                rating=item.rating,
                reason_code=item.reason_code,
                feedback_comment=item.feedback_comment,
                feature_type=item.feature_type,
                created_at=item.created_at,
            )
            for item in feedbacks
        ],
        admin_reviews=[
            AdminChatAdminReview(
                review_id=item.review_id,
                admin_id=item.reviewer_id,
                correctness_label=item.correctness_label,
                citation_label=item.citation_label,
                root_cause=item.root_cause,
                correction_required=item.correction_required,
                corrected_answer=item.corrected_answer,
                review_note=item.review_note,
                created_at=item.created_at,
            )
            for item in admin_reviews
        ],
    )


def get_admin_chat_sessions_by_date(
    db: Session,
    target_date: date,
    page: int,
    size: int,
) -> AdminChatSessionsByDateResult:
    offset = (page - 1) * size
    total_count = count_chat_sessions_by_started_date(db, target_date)
    sessions = list_chat_sessions_by_started_date(db, target_date, offset=offset, limit=size)
    settings = get_settings()
    expiration_threshold = get_current_utc_time() - timedelta(minutes=settings.chat_session_timeout_minutes)

    return AdminChatSessionsByDateResult(
        date=target_date,
        page=page,
        size=size,
        total_count=total_count,
        items=[
            AdminChatSessionSummary(
                session_id=session.session_id,
                user_id=session.user_id,
                total_turns=session.total_turns,
                started_at=session.started_at,
                ended_at=session.ended_at,
                last_activity_at=session.last_activity_at,
                created_at=session.created_at,
                is_expired=_is_chat_session_expired(session.last_activity_at, expiration_threshold),
            )
            for session in sessions
        ]
    )


def get_admin_chat_review_queue(
    db: Session,
    *,
    page: int,
    size: int,
    reason: Optional[AdminChatReviewQueueReason] = None,
) -> AdminChatReviewQueueResult:
    offset = (page - 1) * size
    total_count = count_chat_review_queue_items(db, reason)
    rows = list_chat_review_queue_items(db, reason=reason, offset=offset, limit=size)

    return AdminChatReviewQueueResult(
        page=page,
        size=size,
        total_count=total_count,
        total_pages=_calculate_total_pages(total_count, size),
        items=[
            AdminChatReviewQueueItem(
                chat_log_id=row["chat_log"].chat_log_id,
                session_id=row["chat_log"].session_id,
                user_id=row["chat_log"].user_id,
                question=row["chat_log"].question,
                answer_preview=_build_answer_preview(row["chat_log"].answer),
                answer_status=_get_answer_status_value(row["chat_log"].answer_status),
                review_reason=_resolve_review_reason(row["chat_log"].answer_status),
                negative_feedback_count=row["negative_feedback_count"],
                latest_feedback_reason_code=row["latest_feedback_reason_code"],
                created_at=row["chat_log"].created_at,
            )
            for row in rows
        ],
    )


def save_admin_chat_review(
    db: Session,
    *,
    chat_log_id: int,
    request: AdminChatReviewSaveRequest,
) -> AdminChatAdminReview:
    chat_log = get_chat_log_by_id(db, chat_log_id)
    if chat_log is None:
        raise AppException(CHAT_LOG_NOT_FOUND)

    admin_review = save_chat_admin_review(
        db,
        chat_log_id=chat_log_id,
        reviewer_id=request.admin_id,
        correctness_label=request.correctness_label,
        citation_label=request.citation_label,
        root_cause=request.root_cause,
        correction_required=request.correction_required,
        corrected_answer=request.corrected_answer,
        review_note=request.review_note,
    )
    db.commit()
    db.refresh(admin_review)
    return _build_admin_review_schema(admin_review)


def _is_chat_session_expired(last_activity_at: datetime, expiration_threshold: datetime) -> bool:
    return last_activity_at < expiration_threshold


def _calculate_total_pages(total_count: int, size: int) -> int:
    if total_count == 0:
        return 0
    return (total_count + size - 1) // size


def _build_answer_preview(answer: Optional[str]) -> Optional[str]:
    if answer is None:
        return None
    if len(answer) <= ANSWER_PREVIEW_MAX_LENGTH:
        return answer
    return answer[:ANSWER_PREVIEW_MAX_LENGTH]


def _resolve_review_reason(answer_status) -> AdminChatReviewQueueReason:
    status_value = _get_answer_status_value(answer_status)
    if status_value == "ERROR":
        return "ERROR"
    if status_value == "NO_ANSWER":
        return "NO_ANSWER"
    return "NEGATIVE_FEEDBACK"


def _get_answer_status_value(answer_status) -> str:
    return getattr(answer_status, "value", answer_status)


def _build_admin_review_schema(item) -> AdminChatAdminReview:
    return AdminChatAdminReview(
        review_id=item.review_id,
        admin_id=item.reviewer_id,
        correctness_label=item.correctness_label,
        citation_label=item.citation_label,
        root_cause=item.root_cause,
        correction_required=item.correction_required,
        corrected_answer=item.corrected_answer,
        review_note=item.review_note,
        created_at=item.created_at,
    )
