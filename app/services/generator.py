import re
from dataclasses import dataclass
from typing import Optional

from app.core.config import get_settings
from openai import OpenAI

settings = get_settings()
client = OpenAI(api_key=settings.openai_api_key)


@dataclass(frozen=True)
class AnswerGenerationResult:
    answer: str
    source_url: str
    cited_regulation_chunk_ids: list[int]


def generate_answer(
        question: str, 
        chunks: list[dict],
        dormitory: Optional[str] = None,
        is_fallback: bool = False,
    ) -> AnswerGenerationResult:
    """
    검색된 chunk들을 기반으로 최종 답변 생성
    """
    settings = get_settings()

    if not chunks:
        return AnswerGenerationResult(
            answer=settings.chat_no_answer_message,
            source_url="",
            cited_regulation_chunk_ids=[],
        )

    context = "\n\n".join(
        [
            f"[참고 정보 {index}]\n{chunk['content']}"
            for index, chunk in enumerate(chunks, start=1)
        ]
    )


    fallback_instruction = ""
    if is_fallback and dormitory:
        fallback_instruction = f"""
    사용자는 {dormitory} 기준으로 질문했다.
    현재 참고 정보에는 {dormitory}가 아닌 다른 생활관 정보가 포함될 수 있다.
    {dormitory}에 대한 직접 정보가 참고 정보에 없고, 다른 생활관 정보만 있다면
    "{dormitory}에 대한 직접 정보는 확인되지 않지만, 다른 생활관 기준으로는 ..." 형식으로 답변해라.
    다른 생활관 정보가 질문에 도움이 된다면 관련 정보를 찾을 수 없다고만 답하지 말고, 생활관을 구분해서 안내해라.
    """



    prompt = f"""
너는 기숙사 안내 챗봇이다.
아래 제공된 정보를 기반으로만 질문에 답변해라.
모르는 내용은 추측하지 말고 모른다고 말해라.
질문에서 생활관을 특정하지 않았고 참고 정보가 특정 생활관에만 해당하면, 해당 생활관 기준 답변임을 명확히 밝혀라.
질문에서 생활관을 특정하지 않았더라도 생활관별 구분을 강제로 만들지 말고, 가장 관련 있는 정보 중심으로 간결하게 답변해라.
참고 정보에 생활관 구분이 없거나 공통 규정으로 보이면 일반 답변으로 안내해라.
{fallback_instruction}
답변에는 `[C1]`, `[C2]` 같은 내부 근거 라벨을 절대 출력하지 마라.
출처 문구는 서버가 별도로 붙이므로 답변 본문에는 출처 줄을 만들지 마라.
질문에 답할 정보가 충분하지 않으면 정확히 "{settings.chat_no_answer_message}"라고만 답해라.

[질문]
{question}

[참고 정보]
{context}
"""

    response = client.chat.completions.create(
        model=settings.chat_answer_model,
        temperature=0.3,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    raw_answer = response.choices[0].message.content.strip()
    answer_without_labels = _strip_citation_labels(raw_answer)
    source_chunk = _select_source_chunk(chunks)
    answer = _format_answer_with_source(
        answer_without_labels,
        source_chunk=source_chunk,
        no_answer_message=settings.chat_no_answer_message,
    )
    cited_regulation_chunk_ids = _resolve_used_regulation_chunk_ids(source_chunk)
    source_url = _resolve_source_url(source_chunk)

    return AnswerGenerationResult(
        answer=answer,
        source_url=source_url,
        cited_regulation_chunk_ids=cited_regulation_chunk_ids,
    )


def _strip_citation_labels(answer: str) -> str:
    return re.sub(r"\s*\[C\d+\]", "", answer).strip()


def _select_source_chunk(chunks: list[dict]) -> Optional[dict]:
    if not chunks:
        return None
    return chunks[0]


def _format_answer_with_source(
    answer: str,
    *,
    source_chunk: Optional[dict],
    no_answer_message: str,
) -> str:
    if answer == no_answer_message:
        return answer

    source_line = _build_source_line(source_chunk)
    if not source_line:
        return answer

    answer_body = re.sub(r"\n+\s*출처\s*:.*\Z", "", answer).strip()
    return f"{answer_body}\n\n{source_line}"


def _build_source_line(source_chunk: Optional[dict]) -> str:
    if source_chunk is None:
        return ""

    source = (source_chunk.get("source") or "").strip()
    source_url = (source_chunk.get("source_url") or "").strip()
    if source and source_url:
        return f"출처: {source} ({source_url})"
    if source:
        return f"출처: {source}"
    if source_url:
        return f"출처: {source_url}"
    return ""


def _resolve_used_regulation_chunk_ids(source_chunk: Optional[dict]) -> list[int]:
    if source_chunk is None:
        return []

    regulation_chunk_id = source_chunk.get("regulation_chunk_id")
    if regulation_chunk_id is None:
        return []
    return [regulation_chunk_id]


def _resolve_source_url(source_chunk: Optional[dict]) -> str:
    if source_chunk is None:
        return ""
    return source_chunk.get("source_url", "") or ""
