import json

from app.core.config import get_settings
from app.schemas.notice import NoticeSummaryData
from openai import OpenAI

settings = get_settings()
client = OpenAI(api_key=settings.openai_api_key)


def summarize_notice(title: str, content: str) -> NoticeSummaryData:
    prompt = f"""
다음 공지사항을 읽고 JSON만 반환해줘.

반드시 아래 키를 포함해:
- summary: 2~4문장 핵심 요약
- target_info: 대상자 정보가 있으면 정리, 없으면 null
- schedule_info: 주요 일정 정보가 있으면 정리, 없으면 null
- caution_info: 유의사항 정보가 있으면 정리, 없으면 null

제목:
{title}

본문:
{content}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.3,
        messages=[
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
    )

    response_text = response.choices[0].message.content.strip()
    payload = json.loads(response_text)

    return NoticeSummaryData(
        summary=payload["summary"],
        target_info=payload.get("target_info"),
        schedule_info=payload.get("schedule_info"),
        caution_info=payload.get("caution_info"),
        generated_model=response.model,
    )
