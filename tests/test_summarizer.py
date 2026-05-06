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
    assert result.schedule_info == "일시: 2026년 5월 8일 10시"
    assert result.caution_info == "귀중품은 보관해 주세요.\n소독 시간에는 협조 바랍니다."
    assert result.generated_model == "fake-model"
