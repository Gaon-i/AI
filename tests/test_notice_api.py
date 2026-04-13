"""notice API의 단건 요약 응답 구조를 검증합니다."""

from app.api import notice as notice_api
from app.schemas.notice import NoticeSummaryData


def test_notice_summary_api_returns_title_and_structured_summary(
    client,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        notice_api,
        "summarize_notice",
        lambda title, content: NoticeSummaryData(
            summary="핵심 요약",
            target_info="대상자 정보",
            schedule_info="일정 정보",
            caution_info="유의사항 정보",
            generated_model="fake-model",
        ),
    )

    response = client.post(
        "/api/v1/ai/notice_summary",
        json={
            "title": "기숙사 공지 제목",
            "content": "기숙사 공지 본문",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "title": "기숙사 공지 제목",
        "summary": "핵심 요약",
        "target_info": "대상자 정보",
        "schedule_info": "일정 정보",
        "caution_info": "유의사항 정보",
    }
