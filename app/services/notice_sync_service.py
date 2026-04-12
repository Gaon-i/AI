"""공지 크롤링, 저장, 요약, 만료 삭제를 한 번에 수행하는 서비스입니다."""

from datetime import datetime
from typing import Callable
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.schemas.notice import NoticeListResult
from app.schemas.notice import NoticeSummaryData
from app.schemas.notice import NoticeSyncResult
from app.services.notice_crawler import crawl_recent_notice_payloads
from app.services.notice_service import delete_expired_notices
from app.services.notice_service import get_recent_notice_list
from app.services.notice_service import upsert_notice
from app.services.notice_service import upsert_notice_summary_for_notice
from app.services.summarizer import summarize_notice


def sync_recent_notices(
    db: Session,
    now: datetime,
    retention_days: int = 30,
    client: Optional[httpx.Client] = None,
    summarize_fn: Optional[Callable[[str, str], NoticeSummaryData]] = None,
) -> NoticeSyncResult:
    """최근 공지를 수집해 저장하고 요약까지 생성한 뒤 만료 데이터를 정리합니다."""

    crawled_payloads = crawl_recent_notice_payloads(
        now=now,
        retention_days=retention_days,
        client=client,
    )

    saved_count = 0
    summarized_count = 0
    summarize = summarize_fn or summarize_notice

    for payload in crawled_payloads:
        notice = upsert_notice(db, payload)
        saved_count += 1

        summary_data = summarize(payload.title, payload.content)
        upsert_notice_summary_for_notice(
            db=db,
            notice_id=notice.notice_id,
            payload=summary_data,
        )
        summarized_count += 1

    deleted_count = delete_expired_notices(db, now=now, retention_days=retention_days)

    return NoticeSyncResult(
        crawled_count=len(crawled_payloads),
        saved_count=saved_count,
        summarized_count=summarized_count,
        deleted_count=deleted_count,
    )


def get_recent_notices_for_api(db: Session, now: datetime) -> NoticeListResult:
    """공지 API가 사용할 최신 공지 목록 조회 래퍼입니다."""

    return get_recent_notice_list(db=db, now=now)
