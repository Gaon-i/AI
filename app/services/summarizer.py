import json

from app.core.config import get_settings
from app.schemas.notice import NoticeSummaryData
from openai import OpenAI

settings = get_settings()
client = OpenAI(api_key=settings.openai_api_key)

def _to_text(value) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, list):
        return "\n".join(text for item in value if (text := _to_text(item)))

    if isinstance(value, dict):
        return "\n".join(
            f"{key}: {text}" for key, val in value.items() if (text := _to_text(val))
        )

    return str(value)


def _format_schedule_info(value) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, list):
        return "\n".join(text for item in value if (text := _format_schedule_info(item)))

    if isinstance(value, dict):
        dormitory = _to_text(value.get("dormitory") or value.get("생활관"))
        time = _to_text(value.get("time") or value.get("시간"))
        if dormitory and time:
            return f"{dormitory} {time}"

        return "\n".join(text for val in value.values() if (text := _format_schedule_info(val)))

    return str(value)


def _format_caution_info(value) -> str:
    return _to_text(value)


def summarize_notice(title: str, content: str) -> NoticeSummaryData:
    settings = get_settings()
    prompt = f"""
다음 공지사항을 읽고 JSON만 반환해줘.

반드시 아래 키를 포함해:
- summary: 3~6문장 핵심만 요약
- target_info: 대상자 정보가 있으면 정리, 없으면 null
- schedule_info: 주요 일정 정보가 있으면 문자열로 정리, 없으면 null
- caution_info: 유의사항 정보가 있으면 문자열로 정리, 없으면 null

schedule_info 작성 규칙:
- 반드시 문자열 또는 null로 반환해. 객체나 배열로 반환하지 마.
- date, details 같은 키 이름을 내용에 포함하지 마.
- 요일과 시간만 적어. 양식은 ####년 ##월 ##일, 시간은 오전 또는 오후 #시 이렇게. 
- 생활관 별로 시간이 다르면 생활간 별 시간으로 적어.

caution_info 작성 규칙:
- 반드시 문자열 또는 null로 반환해. 객체나 배열로 반환하지 마.
- caution, warning 같은 키 이름을 내용에 포함하지 마.
- 불이익, 제출 방법, 준비물, 제한사항처럼 사용자가 주의해야 할 내용만 넣어.

제목:
{title}

본문:
{content}
"""

    response = client.chat.completions.create(
        model=settings.notice_summary_model,
        temperature=0.3,
        messages=[
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
    )

    response_text = response.choices[0].message.content.strip()
    payload = json.loads(response_text)

    return NoticeSummaryData(
        summary=_to_text(payload.get("summary")),
        target_info=_to_text(payload.get("target_info")),
        schedule_info=_format_schedule_info(payload.get("schedule_info")),
        caution_info=_format_caution_info(payload.get("caution_info")),
        generated_model=response.model,
    )
