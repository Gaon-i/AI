"""공지 저장, 요약 저장, 목록 조회, 만료 삭제 흐름을 조합하는 서비스 파일입니다."""

from datetime import datetime
from datetime import timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.core.error_codes import NOTICE_DELETE_FAILED
from app.core.error_codes import NOTICE_QUERY_FAILED
from app.core.error_codes import NOTICE_SAVE_FAILED
from app.core.error_codes import NOTICE_SUMMARY_SAVE_FAILED
from app.core.exceptions import AppException
from app.db.models.notice import Notice
from app.db.models.notice_summary import NoticeSummary
from app.repositories.notice_repository import count_notices_since
from app.repositories.notice_repository import create_notice
from app.repositories.notice_repository import create_notice_summary
from app.repositories.notice_repository import delete_notices_older_than
from app.repositories.notice_repository import delete_notice_summaries_older_than
from app.repositories.notice_repository import find_notice_by_source_url
from app.repositories.notice_repository import find_notice_summary_by_notice_id
from app.repositories.notice_repository import list_notices_with_summaries_since
from app.repositories.notice_repository import update_notice
from app.repositories.notice_repository import update_notice_summary
from app.schemas.notice import NoticeListItem
from app.schemas.notice import NoticeListResult
from app.schemas.notice import NoticeSummaryData
from app.schemas.notice import NoticeUpsertPayload


def upsert_notice(db: Session, payload: NoticeUpsertPayload) -> Notice:
    """source_url 기준으로 공지를 생성하거나 최신 값으로 갱신합니다."""

    try:
        existing_notice = find_notice_by_source_url(db, payload.source_url)
        notice = create_notice(db, payload) if existing_notice is None else update_notice(existing_notice, payload)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise AppException(NOTICE_SAVE_FAILED) from exc

    return notice


def upsert_notice_summary_for_notice(
    db: Session,
    notice_id: int,
    payload: NoticeSummaryData,
) -> NoticeSummary:
    """notice_id 기준으로 요약 row를 생성하거나 갱신합니다."""

    try:
        existing_summary = find_notice_summary_by_notice_id(db, notice_id)
        notice_summary = (
            create_notice_summary(db, notice_id, payload)
            if existing_summary is None
            else update_notice_summary(existing_summary, payload)
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise AppException(NOTICE_SUMMARY_SAVE_FAILED) from exc

    return notice_summary


def get_recent_notice_list(
    db: Session,
    now: datetime,
    weekly_days: int = 7,
    monthly_days: int = 30,
) -> NoticeListResult:
    """최근 공지 목록과 주간/월간 집계를 함께 조회합니다."""

    try:
        monthly_cutoff = now - timedelta(days=monthly_days)
        weekly_cutoff = now - timedelta(days=weekly_days)

        rows = list_notices_with_summaries_since(db, monthly_cutoff)
        items = [_build_notice_list_item(notice, notice_summary) for notice, notice_summary in rows]

        return NoticeListResult(
            weekly_count=count_notices_since(db, weekly_cutoff),
            monthly_count=count_notices_since(db, monthly_cutoff),
            items=items,
        )
    except Exception as exc:
        raise AppException(NOTICE_QUERY_FAILED) from exc


def delete_expired_notices(
    db: Session,
    now: datetime,
    retention_days: int = 30,
) -> int:
    """보관 기간을 초과한 공지와 요약을 함께 정리합니다."""

    try:
        cutoff = now - timedelta(days=retention_days)
        delete_notice_summaries_older_than(db, cutoff)
        deleted_notice_count = delete_notices_older_than(db, cutoff)
        db.commit()
        return deleted_notice_count
    except Exception as exc:
        db.rollback()
        raise AppException(NOTICE_DELETE_FAILED) from exc


def _build_notice_list_item(notice: Notice, notice_summary: Optional[NoticeSummary]) -> NoticeListItem:
    """조회 row를 API 응답용 DTO 형태로 정리합니다."""

    return NoticeListItem(
        notice_id=notice.notice_id,
        title=notice.title,
        content=notice.content,
        source_url=notice.source_url,
        posted_at=notice.posted_at,
        summary=notice_summary.summary_text if notice_summary else None,
        target_info=notice_summary.target_info if notice_summary else None,
        schedule_info=notice_summary.schedule_info if notice_summary else None,
        caution_info=notice_summary.caution_info if notice_summary else None,
    )
