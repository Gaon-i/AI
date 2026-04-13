"""notice 목록 조회 API 응답 구조를 검증합니다."""

from datetime import datetime

from app.api import notice as notice_api
from app.schemas.notice import NoticeListItem
from app.schemas.notice import NoticeListResult


def test_notice_list_api_returns_counts_and_notice_items(client, monkeypatch) -> None:
    monkeypatch.setattr(
        notice_api,
        "get_recent_notices_for_api",
        lambda **_kwargs: NoticeListResult(
            weekly_count=1,
            monthly_count=2,
            items=[
                NoticeListItem(
                    notice_id=1,
                    title="기숙사 점검 안내",
                    source_url="https://example.com/notices/1",
                    posted_at=datetime(2026, 4, 12, 0, 0, 0),
                    summary="핵심 요약",
                    target_info="전체 입사생",
                    schedule_info="4월 12일",
                    caution_info="외출 전 정리",
                )
            ],
        ),
    )

    response = client.get("/api/v1/notices")

    assert response.status_code == 200
    assert response.json() == {
        "weekly_count": 1,
        "monthly_count": 2,
        "items": [
            {
                "notice_id": 1,
                "title": "기숙사 점검 안내",
                "source_url": "https://example.com/notices/1",
                "posted_at": "2026-04-12T00:00:00",
                "summary": "핵심 요약",
                "target_info": "전체 입사생",
                "schedule_info": "4월 12일",
                "caution_info": "외출 전 정리",
            }
        ],
    }
