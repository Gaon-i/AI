import os

from app.core.config import get_settings
from openai import OpenAI

settings = get_settings()
client = OpenAI(api_key=settings.openai_api_key)


def summarize_notice(title: str, content: str) -> str:
    prompt = f"""
다음 공지사항을 2~4문장으로 간단명료하게 요약해줘.
중요한 일정, 장소, 대상, 유의사항이 있으면 포함해줘.

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
        ]
    )

    return response.choices[0].message.content.strip()