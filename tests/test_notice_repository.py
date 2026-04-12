"""notice repository가 저장/조회/삭제 매핑을 올바르게 처리하는지 검증하는 테스트 파일입니다."""

from datetime import datetime

from app.repositories.notice_repository import create_notice
from app.repositories.notice_repository import create_notice_summary
from app.repositories.notice_repository import update_notice
from app.repositories.notice_repository import update_notice_summary
from app.schemas.notice import NoticeSummaryData
from app.schemas.notice import NoticeUpsertPayload


class FakeSession:
    """실제 DB 없이 add/flush/refresh에 전달된 ORM 객체만 확인하기 위한 테스트 더블입니다."""

    def __init__(self) -> None:
        self.added = None
        self.flush_called = False
        self.refresh_called = False

    def add(self, value) -> None:
        self.added = value

    def flush(self) -> None:
        self.flush_called = True

    def refresh(self, value) -> None:
        self.refresh_called = True


def test_create_notice_maps_payload_to_model() -> None:
    db = FakeSession()
    payload = NoticeUpsertPayload(
        title="기숙사 화재대피훈련 안내",
        content="화재대피훈련 참여보고서를 제출해 주세요.",
        source_url="https://example.com/notices/1",
        posted_at=datetime(2026, 3, 19, 0, 0, 0),
    )

    notice = create_notice(db, payload)

    assert db.added is notice
    assert notice.title == payload.title
    assert notice.content == payload.content
    assert notice.source_url == payload.source_url
    assert notice.posted_at == payload.posted_at
    assert db.flush_called is True
    assert db.refresh_called is True


def test_update_notice_updates_existing_model_fields() -> None:
    notice = type(
        "NoticeStub",
        (),
        {
            "title": "old",
            "content": "old content",
            "posted_at": datetime(2026, 3, 1, 0, 0, 0),
            "collected_at": None,
        },
    )()
    payload = NoticeUpsertPayload(
        title="새 공지 제목",
        content="새 공지 본문",
        source_url="https://example.com/notices/1",
        posted_at=datetime(2026, 3, 19, 0, 0, 0),
        collected_at=datetime(2026, 3, 19, 12, 0, 0),
    )

    updated_notice = update_notice(notice, payload)

    assert updated_notice.title == "새 공지 제목"
    assert updated_notice.content == "새 공지 본문"
    assert updated_notice.posted_at == datetime(2026, 3, 19, 0, 0, 0)
    assert updated_notice.collected_at == datetime(2026, 3, 19, 12, 0, 0)


def test_create_notice_summary_maps_payload_to_model() -> None:
    db = FakeSession()
    payload = NoticeSummaryData(
        summary="화재대피훈련 온라인 교육 참여 및 보고서 제출 안내입니다.",
        target_info="기숙사 입사생 전체",
        schedule_info="2026-03-25부터 2026-03-31 21시까지",
        caution_info="미제출 시 벌점 2점 부여",
        generated_model="gpt-4o-mini",
    )

    notice_summary = create_notice_summary(db, 1, payload)

    assert db.added is notice_summary
    assert notice_summary.notice_id == 1
    assert notice_summary.summary_text == payload.summary
    assert notice_summary.target_info == payload.target_info
    assert notice_summary.schedule_info == payload.schedule_info
    assert notice_summary.caution_info == payload.caution_info
    assert notice_summary.generated_model == payload.generated_model
    assert db.flush_called is True
    assert db.refresh_called is True


def test_update_notice_summary_updates_existing_model_fields() -> None:
    notice_summary = type(
        "NoticeSummaryStub",
        (),
        {
            "summary_text": "old summary",
            "target_info": "old target",
            "schedule_info": "old schedule",
            "caution_info": "old caution",
            "generated_model": "old-model",
            "generated_at": None,
        },
    )()
    payload = NoticeSummaryData(
        summary="새 요약",
        target_info="신규 대상",
        schedule_info="신규 일정",
        caution_info="신규 유의사항",
        generated_model="gpt-4o-mini",
    )

    updated_summary = update_notice_summary(notice_summary, payload)

    assert updated_summary.summary_text == "새 요약"
    assert updated_summary.target_info == "신규 대상"
    assert updated_summary.schedule_info == "신규 일정"
    assert updated_summary.caution_info == "신규 유의사항"
    assert updated_summary.generated_model == "gpt-4o-mini"
    assert isinstance(updated_summary.generated_at, datetime)
