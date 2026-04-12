"""notice 및 notice_summary 테이블의 저장/조회 책임을 분리한 repository 파일입니다."""

from datetime import datetime
from datetime import timezone
from typing import Optional

from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import outerjoin
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.notice import Notice
from app.db.models.notice_summary import NoticeSummary
from app.schemas.notice import NoticeSummaryData
from app.schemas.notice import NoticeUpsertPayload


def find_notice_by_source_url(db: Session, source_url: str) -> Optional[Notice]:
    """같은 원문 링크의 공지가 이미 저장되어 있는지 확인합니다."""

    statement = select(Notice).where(Notice.source_url == source_url)
    return db.execute(statement).scalar_one_or_none()


def create_notice(db: Session, payload: NoticeUpsertPayload) -> Notice:
    """새 공지 row를 생성합니다."""

    notice = Notice(
        title=payload.title,
        content=payload.content,
        source_url=payload.source_url,
        posted_at=payload.posted_at,
        collected_at=payload.collected_at,
    )
    db.add(notice)
    db.flush()
    db.refresh(notice)
    return notice


def update_notice(notice: Notice, payload: NoticeUpsertPayload) -> Notice:
    """같은 source_url의 기존 공지를 최신 본문과 수집 시각으로 갱신합니다."""

    notice.title = payload.title
    notice.content = payload.content
    notice.posted_at = payload.posted_at
    if payload.collected_at is not None:
        notice.collected_at = payload.collected_at
    return notice


def find_notice_summary_by_notice_id(db: Session, notice_id: int) -> Optional[NoticeSummary]:
    """원본 공지에 연결된 요약 row가 이미 있는지 확인합니다."""

    statement = select(NoticeSummary).where(NoticeSummary.notice_id == notice_id)
    return db.execute(statement).scalar_one_or_none()


def create_notice_summary(db: Session, notice_id: int, payload: NoticeSummaryData) -> NoticeSummary:
    """새 공지 요약 row를 생성합니다."""

    notice_summary = NoticeSummary(
        notice_id=notice_id,
        summary_text=payload.summary,
        target_info=payload.target_info,
        schedule_info=payload.schedule_info,
        caution_info=payload.caution_info,
        generated_model=payload.generated_model,
    )
    db.add(notice_summary)
    db.flush()
    db.refresh(notice_summary)
    return notice_summary


def update_notice_summary(notice_summary: NoticeSummary, payload: NoticeSummaryData) -> NoticeSummary:
    """기존 공지 요약 row를 최신 생성 결과로 갱신합니다."""

    notice_summary.summary_text = payload.summary
    notice_summary.target_info = payload.target_info
    notice_summary.schedule_info = payload.schedule_info
    notice_summary.caution_info = payload.caution_info
    notice_summary.generated_model = payload.generated_model
    # 서비스가 commit 직후 반환해도 concrete timestamp를 바로 쓸 수 있도록 Python 시각을 저장합니다.
    notice_summary.generated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    return notice_summary


def list_notices_with_summaries_since(
    db: Session,
    posted_since: datetime,
) -> list[tuple[Notice, Optional[NoticeSummary]]]:
    """지정 시각 이후 공지를 요약과 함께 최신순으로 조회합니다."""

    joined_table = outerjoin(Notice, NoticeSummary, Notice.notice_id == NoticeSummary.notice_id)
    statement = (
        select(Notice, NoticeSummary)
        .select_from(joined_table)
        .where(Notice.posted_at >= posted_since)
        .order_by(Notice.posted_at.desc(), Notice.notice_id.desc())
    )
    return db.execute(statement).all()


def count_notices_since(db: Session, posted_since: datetime) -> int:
    """지정 시각 이후 공지 수를 셉니다."""

    statement = select(func.count(Notice.notice_id)).where(Notice.posted_at >= posted_since)
    return db.execute(statement).scalar_one()


def delete_notice_summaries_older_than(db: Session, posted_before: datetime) -> int:
    """만료 공지에 연결된 요약 row를 먼저 삭제합니다."""

    expired_notice_ids = select(Notice.notice_id).where(Notice.posted_at < posted_before)
    statement = delete(NoticeSummary).where(NoticeSummary.notice_id.in_(expired_notice_ids))
    return db.execute(statement).rowcount or 0


def delete_notices_older_than(db: Session, posted_before: datetime) -> int:
    """지정 시각보다 오래된 공지 row를 삭제합니다."""

    statement = delete(Notice).where(Notice.posted_at < posted_before)
    return db.execute(statement).rowcount or 0
