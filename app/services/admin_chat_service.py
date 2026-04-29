from datetime import datetime
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.error_codes import CHAT_LOG_NOT_FOUND
from app.core.exceptions import AppException
from app.core.time_utils import get_current_utc_time
from app.repositories.admin_chat_repository import get_chat_log_by_id
from app.repositories.admin_chat_repository import list_chat_error_logs_by_chat_log_id
from app.repositories.admin_chat_repository import list_chat_retrieval_results_by_chat_log_id
from app.repositories.admin_chat_repository import list_recent_chat_sessions
from app.schemas.admin_chat import AdminChatErrorLog
from app.schemas.admin_chat import AdminChatLogDetail
from app.schemas.admin_chat import AdminChatRetrievalResult
from app.schemas.admin_chat import AdminRecentChatSessionsResult
from app.schemas.admin_chat import AdminChatSessionSummary


def get_admin_chat_log_detail(db: Session, chat_log_id: int) -> AdminChatLogDetail:
    chat_log = get_chat_log_by_id(db, chat_log_id)
    if chat_log is None:
        raise AppException(CHAT_LOG_NOT_FOUND)
    retrieval_results = list_chat_retrieval_results_by_chat_log_id(db, chat_log_id)
    error_logs = list_chat_error_logs_by_chat_log_id(db, chat_log_id)

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
    )


def get_recent_admin_chat_sessions(db: Session) -> AdminRecentChatSessionsResult:
    sessions = list_recent_chat_sessions(db, limit=10)
    return AdminRecentChatSessionsResult(
        items=[
            AdminChatSessionSummary(
                session_id=session.session_id,
                user_id=session.user_id,
                total_turns=session.total_turns,
                started_at=session.started_at,
                ended_at=session.ended_at,
                last_activity_at=session.last_activity_at,
                entry_point=session.entry_point,
                is_returning_user=session.is_returning_user,
                utm_source=session.utm_source,
                utm_medium=session.utm_medium,
                utm_campaign=session.utm_campaign,
                created_at=session.created_at,
                is_expired=_is_chat_session_expired(session.last_activity_at),
            )
            for session in sessions
        ]
    )


def _is_chat_session_expired(last_activity_at: datetime) -> bool:
    settings = get_settings()
    expiration_threshold = get_current_utc_time() - timedelta(minutes=settings.chat_session_timeout_minutes)
    return last_activity_at < expiration_threshold
