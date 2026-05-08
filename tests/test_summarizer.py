import json
from types import SimpleNamespace

from app.services import summarizer


def test_summarize_notice_normalizes_structured_llm_fields(monkeypatch) -> None:
    payload = {
        "summary": {"핵심": "생활관 소독 안내입니다."},
        "target_info": {"소독 대상": "전체 생활관"},
        "schedule_info": {"일시": "2026년 5월 8일 10시"},
        "caution_info": ["귀중품은 보관해 주세요.", "소독 시간에는 협조 바랍니다."],
    }

    fake_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=json.dumps(payload, ensure_ascii=False))
            )
        ],
        model="fake-model",
    )
    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **_kwargs: fake_response)
        )
    )
    monkeypatch.setattr(summarizer, "client", fake_client)

    result = summarizer.summarize_notice("소독 안내", "생활관 소독을 진행합니다.")

    assert result.summary == "핵심: 생활관 소독 안내입니다."
    assert result.target_info == "소독 대상: 전체 생활관"
    assert result.schedule_info == "2026년 5월 8일 10시"
    assert result.caution_info == "귀중품은 보관해 주세요.\n소독 시간에는 협조 바랍니다."
    assert result.generated_model == "fake-model"


def test_summarize_notice_removes_structured_schedule_keys(monkeypatch) -> None:
    payload = {
        "summary": "요약",
        "target_info": None,
        "schedule_info": {
            "control_period": "2026년 5월 13일 수요일 오전 11시 이후",
            "details": [
                {"dormitory": "제1학생생활관", "time": "오후 1시부터"},
                {"dormitory": "제2학생생활관", "time": "오전 9시부터"},
            ],
        },
        "caution_info": "신청 기간을 확인해 주세요.",
    }

    fake_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=json.dumps(payload, ensure_ascii=False))
            )
        ],
        model="fake-model",
    )
    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **_kwargs: fake_response)
        )
    )
    monkeypatch.setattr(summarizer, "client", fake_client)

    result = summarizer.summarize_notice("일정 안내", "2026. 5. 13(수) 11:00 이후")

    assert result.schedule_info == (
        "2026년 5월 13일 수요일 오전 11시 이후\n"
        "제1학생생활관 오후 1시부터\n"
        "제2학생생활관 오전 9시부터"
    )
    assert "control_period" not in result.schedule_info
    assert "details" not in result.schedule_info
    assert result.caution_info == "신청 기간을 확인해 주세요."


def test_to_text_omits_empty_nested_values() -> None:
    assert summarizer._to_text(["A", None, "  ", "B"]) == "A\nB"
    assert summarizer._to_text({"대상": "전체", "비고": None, "공백": "  "}) == "대상: 전체"
