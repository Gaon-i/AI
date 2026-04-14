
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
        model="gpt-4o-mini",
        temperature=0.3,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    answer = response.choices[0].message.content.strip()

    # 첫 번째 chunk의 source_url 사용
    source_url = chunks[0].get("source_url", "")

    return answer, source_url


def generate_grouped_answer(question: str, dormitory_chunks: dict[str, list[dict]]) -> tuple[str, str]:
    """
    dormitory가 없을 때 생활관별 검색 결과를 나눠서 답변 생성
    """
    available = {k: v for k, v in dormitory_chunks.items() if v}

    if not available:
        return "관련 정보를 찾을 수 없습니다.", ""

    context_parts = []
    first_source_url = ""

    for dormitory, chunks in available.items():
        if not first_source_url and chunks:
            first_source_url = chunks[0].get("source_url", "")

        joined = "\n".join([f"- {chunk['content']}" for chunk in chunks])
        context_parts.append(f"[{dormitory}]\n{joined}")

    context = "\n\n".join(context_parts)

    prompt = f"""
너는 기숙사 안내 챗봇이다.
아래 제공된 정보를 기반으로만 답변해라.
반드시 생활관별로 구분해서 설명해라.
정보가 없는 생활관은 언급하지 않아도 된다.
모르는 내용은 추측하지 말고 제공된 정보 범위에서만 답변해라.

출력 형식 예시:
제1학생생활관: ...
제2학생생활관: ...
제3학생생활관: ...

[질문]
{question}

[생활관별 참고 정보]
{context}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.3,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    answer = response.choices[0].message.content.strip()
    return answer, first_source_url