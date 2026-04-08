import os

from app.core.config import get_settings
from openai import OpenAI

settings = get_settings()
client = OpenAI(api_key=settings.openai_api_key)


def generate_answer(question: str, chunks: list[dict]) -> tuple[str, str]:
    """
    검색된 chunk들을 기반으로 최종 답변 생성
    """

    if not chunks:
        return "관련 정보를 찾을 수 없습니다.", ""

    context = "\n\n".join([chunk["content"] for chunk in chunks])

    prompt = f"""
너는 기숙사 안내 챗봇이다.
아래 제공된 정보를 기반으로만 질문에 답변해라.
모르는 내용은 추측하지 말고 모른다고 말해라.

[질문]
{question}

[참고 정보]
{context}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.3,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    answer = response.choices[0].message.content.strip()

    # 첫 번째 chunk의 source_url 사용
    source_url = chunks[0].get("source_url", "")

    return answer, source_url