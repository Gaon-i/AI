"""notice 서비스의 저장/조회/삭제 비즈니스 흐름을 검증하는 테스트 파일입니다."""

from datetime import datetime

import pytest

from app.core.error_codes import NOTICE_DELETE_FAILED
from app.core.error_codes import NOTICE_QUERY_FAILED
from app.core.error_codes import NOTICE_SAVE_FAILED
from app.core.error_codes import NOTICE_SUMMARY_SAVE_FAILED
from app.core.exceptions import AppException
from app.schemas.notice import NoticeSummaryData
from app.schemas.notice import NoticeUpsertPayload
from app.services import notice_service


class FakeSession:
    """DB 세션 전체를 쓰지 않고 commit/rollback 호출 여부만 확인하기 위한 테스트 더블입니다."""

    def __init__(self) -> None:
        self.commit_called = False
        self.rollback_called = False

    def commit(self) -> None:
        self.commit_called = True

    def rollback(self) -> None:
        self.rollback_called = True


def build_notice_payload() -> NoticeUpsertPayload:
    return NoticeUpsertPayload(
        title="기숙사 화재대피훈련 안내",
        content="화재대피훈련 참여보고서를 제출해 주세요.",
        source_url="https://example.com/notices/1",
        posted_at=datetime(2026, 3, 19, 0, 0, 0),
        collected_at=datetime(2026, 3, 19, 12, 0, 0),
    )


def build_summary_payload() -> NoticeSummaryData:
    return NoticeSummaryData(
        summary="화재대피훈련 온라인 교육 참여 및 보고서 제출 안내입니다.",
        target_info="기숙사 입사생 전체",
        schedule_info="2026-03-25부터 2026-03-31 21시까지",
        caution_info="미제출 시 벌점 2점 부여",
        generated_model="gpt-4o-mini",
    )


def test_upsert_notice_creates_when_source_url_is_new(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = build_notice_payload()
    db = FakeSession()

    class SavedNotice:
        notice_id = 1
        title = payload.title
        content = payload.content
        source_url = payload.source_url
        posted_at = payload.posted_at

    monkeypatch.setattr(notice_service, "find_notice_by_source_url", lambda *_: None)
    monkeypatch.setattr(notice_service, "create_notice", lambda *_args: SavedNotice())

    notice = notice_service.upsert_notice(db, payload)

    assert notice.notice_id == 1
    assert db.commit_called is True
    assert db.rollback_called is False


def test_upsert_notice_updates_existing_notice(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = build_notice_payload()
    db = FakeSession()
    existing_notice = type("ExistingNotice", (), {"notice_id": 3})()

    monkeypatch.setattr(notice_service, "find_notice_by_source_url", lambda *_: existing_notice)
    monkeypatch.setattr(notice_service, "update_notice", lambda notice, notice_payload: notice)

    notice = notice_service.upsert_notice(db, payload)

    assert notice.notice_id == 3
    assert db.commit_called is True
    assert db.rollback_called is False


def test_upsert_notice_wraps_unexpected_error(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = build_notice_payload()
    db = FakeSession()

    monkeypatch.setattr(notice_service, "find_notice_by_source_url", lambda *_: None)
    monkeypatch.setattr(
        notice_service,
        "create_notice",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("insert failed")),
    )

    with pytest.raises(AppException) as exc_info:
        notice_service.upsert_notice(db, payload)

    assert exc_info.value.error_code == NOTICE_SAVE_FAILED
    assert db.commit_called is False
    assert db.rollback_called is True


def test_upsert_notice_in_transaction_does_not_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = build_notice_payload()
    db = FakeSession()

    monkeypatch.setattr(notice_service, "find_notice_by_source_url", lambda *_: None)
    monkeypatch.setattr(
        notice_service,
        "create_notice",
        lambda *_args: type("SavedNotice", (), {"notice_id": 1})(),
    )

    notice = notice_service.upsert_notice_in_transaction(db, payload)

    assert notice.notice_id == 1
    assert db.commit_called is False
    assert db.rollback_called is False


def test_upsert_notice_summary_creates_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = build_summary_payload()
    db = FakeSession()

    class SavedSummary:
        notice_summary_id = 7
        notice_id = 1
        summary_text = payload.summary

    monkeypatch.setattr(notice_service, "find_notice_summary_by_notice_id", lambda *_: None)
    monkeypatch.setattr(notice_service, "create_notice_summary", lambda *_args: SavedSummary())

    notice_summary = notice_service.upsert_notice_summary_for_notice(db, 1, payload)

    assert notice_summary.notice_summary_id == 7
    assert db.commit_called is True
    assert db.rollback_called is False


def test_upsert_notice_summary_wraps_unexpected_error(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = build_summary_payload()
    db = FakeSession()

    monkeypatch.setattr(notice_service, "find_notice_summary_by_notice_id", lambda *_: None)
    monkeypatch.setattr(
        notice_service,
        "create_notice_summary",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("summary insert failed")),
    )

    with pytest.raises(AppException) as exc_info:
        notice_service.upsert_notice_summary_for_notice(db, 1, payload)

    assert exc_info.value.error_code == NOTICE_SUMMARY_SAVE_FAILED
    assert db.commit_called is False
    assert db.rollback_called is True


def test_upsert_notice_summary_in_transaction_does_not_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = build_summary_payload()
    db = FakeSession()

    monkeypatch.setattr(notice_service, "find_notice_summary_by_notice_id", lambda *_: None)
    monkeypatch.setattr(
        notice_service,
        "create_notice_summary",
        lambda *_args: type("SavedSummary", (), {"notice_summary_id": 7})(),
    )

    notice_summary = notice_service.upsert_notice_summary_for_notice_in_transaction(db, 1, payload)

    assert notice_summary.notice_summary_id == 7
    assert db.commit_called is False
    assert db.rollback_called is False


def test_get_recent_notice_list_returns_counts_and_items(monkeypatch: pytest.MonkeyPatch) -> None:
    db = FakeSession()
    now = datetime(2026, 4, 12, 12, 0, 0)

    notice = type(
        "NoticeStub",
        (),
        {
            "notice_id": 1,
            "title": "기숙사 화재대피훈련 안내",
            "content": "화재대피훈련 참여보고서를 제출해 주세요.",
            "source_url": "https://example.com/notices/1",
            "posted_at": datetime(2026, 3, 19, 0, 0, 0),
        },
    )()
    notice_summary = type(
        "NoticeSummaryStub",
        (),
        {
            "summary_text": "핵심 요약",
            "target_info": "대상자 정보",
            "schedule_info": "주요 일정",
            "caution_info": "유의사항",
        },
    )()

    monkeypatch.setattr(
        notice_service,
        "list_notices_with_summaries_since",
        lambda *_args: [(notice, notice_summary)],
    )
    monkeypatch.setattr(
        notice_service,
        "count_notices_since",
        lambda _db, posted_since: 1 if posted_since <= datetime(2026, 4, 5, 12, 0, 0) else 3,
    )

    result = notice_service.get_recent_notice_list(db, now)

    assert result.weekly_count == 1
    assert result.monthly_count == 1
    assert len(result.items) == 1
    assert result.items[0].title == "기숙사 화재대피훈련 안내"
    assert result.items[0].summary == "핵심 요약"


def test_get_recent_notice_list_wraps_query_error(monkeypatch: pytest.MonkeyPatch) -> None:
    db = FakeSession()

    monkeypatch.setattr(
        notice_service,
        "list_notices_with_summaries_since",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("query failed")),
    )

    with pytest.raises(AppException) as exc_info:
        notice_service.get_recent_notice_list(db, datetime(2026, 4, 12, 12, 0, 0))

    assert exc_info.value.error_code == NOTICE_QUERY_FAILED


def test_get_recent_notice_list_counts_notices_using_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    db = FakeSession()
    now = datetime(2026, 4, 12, 12, 0, 0)

    monkeypatch.setattr(
        notice_service,
        "list_notices_with_summaries_since",
        lambda *_args: [],
    )

    captured_cutoffs: list[datetime] = []

    def fake_count_notices_since(_db, posted_since: datetime) -> int:
        captured_cutoffs.append(posted_since)
        return 0

    monkeypatch.setattr(
        notice_service,
        "count_notices_since",
        fake_count_notices_since,
    )

    result = notice_service.get_recent_notice_list(db, now)

    assert result.weekly_count == 0
    assert result.monthly_count == 0
    assert captured_cutoffs == [
        datetime(2026, 4, 5, 12, 0, 0),
        datetime(2026, 3, 13, 12, 0, 0),
    ]


def test_delete_expired_notices_deletes_summaries_then_notices(monkeypatch: pytest.MonkeyPatch) -> None:
    db = FakeSession()
    call_order: list[str] = []

    monkeypatch.setattr(
        notice_service,
        "delete_notice_summaries_older_than",
        lambda *_args: call_order.append("summary") or 2,
    )
    monkeypatch.setattr(
        notice_service,
        "delete_notices_older_than",
        lambda *_args: call_order.append("notice") or 2,
    )

    deleted_count = notice_service.delete_expired_notices(db, datetime(2026, 4, 12, 12, 0, 0))

    assert deleted_count == 2
    assert call_order == ["summary", "notice"]
    assert db.commit_called is True
    assert db.rollback_called is False


def test_delete_expired_notices_wraps_delete_error(monkeypatch: pytest.MonkeyPatch) -> None:
    db = FakeSession()

    monkeypatch.setattr(
        notice_service,
        "delete_notice_summaries_older_than",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("delete failed")),
    )

    with pytest.raises(AppException) as exc_info:
        notice_service.delete_expired_notices(db, datetime(2026, 4, 12, 12, 0, 0))

    assert exc_info.value.error_code == NOTICE_DELETE_FAILED
    assert db.commit_called is False
    assert db.rollback_called is True
