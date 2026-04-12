"""notice sync 서비스가 크롤링부터 저장/요약/삭제까지 연결하는지 검증합니다."""

from datetime import datetime

from app.schemas.notice import NoticeSummaryData
from app.schemas.notice import NoticeUpsertPayload
from app.services import notice_sync_service


class FakeSession:
    pass


def build_payload(title: str, source_url: str) -> NoticeUpsertPayload:
    return NoticeUpsertPayload(
        title=title,
        content=f"{title} 본문",
        source_url=source_url,
        posted_at=datetime(2026, 4, 10, 0, 0, 0),
        collected_at=datetime(2026, 4, 12, 12, 0, 0),
    )


def test_sync_recent_notices_runs_crawl_save_summarize_delete(monkeypatch) -> None:
    db = FakeSession()
    saved_notice_ids: list[int] = []
    saved_summaries: list[NoticeSummaryData] = []

    monkeypatch.setattr(
        notice_sync_service,
        "crawl_recent_notice_payloads",
        lambda **_kwargs: [
            build_payload("공지 1", "https://example.com/notices/1"),
            build_payload("공지 2", "https://example.com/notices/2"),
        ],
    )

    def fake_upsert_notice(_db, payload):
        notice_id = len(saved_notice_ids) + 1
        saved_notice_ids.append(notice_id)
        return type("NoticeStub", (), {"notice_id": notice_id, "title": payload.title})()

    def fake_upsert_notice_summary_for_notice(db, notice_id, payload):
        saved_summaries.append(payload)
        return type("NoticeSummaryStub", (), {"notice_id": notice_id})()

    monkeypatch.setattr(notice_sync_service, "upsert_notice", fake_upsert_notice)
    monkeypatch.setattr(
        notice_sync_service,
        "upsert_notice_summary_for_notice",
        fake_upsert_notice_summary_for_notice,
    )
    monkeypatch.setattr(notice_sync_service, "find_notice_by_source_url", lambda *_args: None)
    monkeypatch.setattr(notice_sync_service, "find_notice_summary_by_notice_id", lambda *_args: None)
    monkeypatch.setattr(notice_sync_service, "delete_expired_notices", lambda *_args, **_kwargs: 3)

    result = notice_sync_service.sync_recent_notices(
        db=db,
        now=datetime(2026, 4, 12, 12, 0, 0),
        summarize_fn=lambda title, content: NoticeSummaryData(
            summary=f"{title} 요약",
            target_info="대상자 정보",
            schedule_info="일정 정보",
            caution_info="유의사항 정보",
            generated_model="fake-model",
        ),
    )

    assert result.crawled_count == 2
    assert result.saved_count == 2
    assert result.summarized_count == 2
    assert result.deleted_count == 3
    assert [payload.summary for payload in saved_summaries] == ["공지 1 요약", "공지 2 요약"]
    assert [payload.target_info for payload in saved_summaries] == ["대상자 정보", "대상자 정보"]


def test_sync_recent_notices_preserves_structured_summary_fields(monkeypatch) -> None:
    db = FakeSession()
    captured_payloads: list[NoticeSummaryData] = []

    monkeypatch.setattr(
        notice_sync_service,
        "crawl_recent_notice_payloads",
        lambda **_kwargs: [build_payload("공지 1", "https://example.com/notices/1")],
    )
    monkeypatch.setattr(
        notice_sync_service,
        "upsert_notice",
        lambda *_args: type("NoticeStub", (), {"notice_id": 1})(),
    )
    monkeypatch.setattr(
        notice_sync_service,
        "upsert_notice_summary_for_notice",
        lambda db, notice_id, payload: captured_payloads.append(payload)
        or type("NoticeSummaryStub", (), {"notice_id": notice_id})(),
    )
    monkeypatch.setattr(notice_sync_service, "find_notice_by_source_url", lambda *_args: None)
    monkeypatch.setattr(notice_sync_service, "find_notice_summary_by_notice_id", lambda *_args: None)
    monkeypatch.setattr(notice_sync_service, "delete_expired_notices", lambda *_args, **_kwargs: 0)

    notice_sync_service.sync_recent_notices(
        db=db,
        now=datetime(2026, 4, 12, 12, 0, 0),
        summarize_fn=lambda title, content: NoticeSummaryData(
            summary="구조화 요약",
            target_info="신입사생",
            schedule_info="4월 15일까지",
            caution_info="미제출 시 불이익",
            generated_model="fake-model",
        ),
    )

    assert len(captured_payloads) == 1
    assert captured_payloads[0].target_info == "신입사생"
    assert captured_payloads[0].schedule_info == "4월 15일까지"
    assert captured_payloads[0].caution_info == "미제출 시 불이익"


def test_sync_recent_notices_skips_resummarizing_unchanged_notice(monkeypatch) -> None:
    db = FakeSession()
    summary_call_count = 0

    monkeypatch.setattr(
        notice_sync_service,
        "crawl_recent_notice_payloads",
        lambda **_kwargs: [build_payload("공지 1", "https://example.com/notices/1")],
    )
    monkeypatch.setattr(
        notice_sync_service,
        "find_notice_by_source_url",
        lambda *_args: type(
            "ExistingNoticeStub",
            (),
            {
                "notice_id": 1,
                "title": "공지 1",
                "content": "공지 1 본문",
                "posted_at": datetime(2026, 4, 10, 0, 0, 0),
            },
        )(),
    )
    monkeypatch.setattr(
        notice_sync_service,
        "upsert_notice",
        lambda *_args: type("NoticeStub", (), {"notice_id": 1})(),
    )
    monkeypatch.setattr(
        notice_sync_service,
        "find_notice_summary_by_notice_id",
        lambda *_args: object(),
    )
    monkeypatch.setattr(
        notice_sync_service,
        "upsert_notice_summary_for_notice",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("should not update summary")),
    )
    monkeypatch.setattr(notice_sync_service, "delete_expired_notices", lambda *_args, **_kwargs: 0)

    def fake_summarize(*_args) -> NoticeSummaryData:
        nonlocal summary_call_count
        summary_call_count += 1
        return NoticeSummaryData(summary="요약")

    result = notice_sync_service.sync_recent_notices(
        db=db,
        now=datetime(2026, 4, 12, 12, 0, 0),
        summarize_fn=fake_summarize,
    )

    assert result.crawled_count == 1
    assert result.saved_count == 1
    assert result.summarized_count == 0
    assert summary_call_count == 0


def test_get_recent_notices_for_api_delegates_to_notice_service(monkeypatch) -> None:
    db = FakeSession()

    monkeypatch.setattr(
        notice_sync_service,
        "get_recent_notice_list",
        lambda **_kwargs: type(
            "NoticeListResultStub",
            (),
            {
                "weekly_count": 1,
                "monthly_count": 2,
                "items": [],
            },
        )(),
    )

    result = notice_sync_service.get_recent_notices_for_api(
        db=db,
        now=datetime(2026, 4, 12, 12, 0, 0),
    )

    assert result.weekly_count == 1
    assert result.monthly_count == 2
