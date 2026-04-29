import re
from dataclasses import dataclass

from app.core.config import get_settings
from openai import OpenAI

settings = get_settings()
client = OpenAI(api_key=settings.openai_api_key)


@dataclass(frozen=True)
class AnswerGenerationResult:
    answer: str
    source_url: str
    cited_regulation_chunk_ids: list[int]


def generate_answer(question: str, chunks: list[dict]) -> AnswerGenerationResult:
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
            f"[{chunk['citation_label']}] {chunk['content']}"
            for chunk in chunks
        ]
    )

    prompt = f"""
너는 기숙사 안내 챗봇이다.
아래 제공된 정보를 기반으로만 질문에 답변해라.
모르는 내용은 추측하지 말고 모른다고 말해라.
질문에서 생활관을 특정하지 않았고 참고 정보가 특정 생활관에만 해당하면, 해당 생활관 기준 답변임을 명확히 밝혀라.
질문에서 생활관을 특정하지 않았더라도 생활관별 구분을 강제로 만들지 말고, 가장 관련 있는 정보 중심으로 간결하게 답변해라.
참고 정보에 생활관 구분이 없거나 공통 규정으로 보이면 일반 답변으로 안내해라.
답변에서 참고한 근거가 있으면 문장 끝에 반드시 근거 라벨을 붙여라.
근거 라벨은 제공된 형식 그대로 `[C1]`, `[C2]`처럼 사용해라.
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

    answer = response.choices[0].message.content.strip()
    cited_regulation_chunk_ids = _extract_cited_regulation_chunk_ids(answer, chunks)
    source_url = _resolve_source_url(chunks, cited_regulation_chunk_ids)

    return AnswerGenerationResult(
        answer=answer,
        source_url=source_url,
        cited_regulation_chunk_ids=cited_regulation_chunk_ids,
    )


def _extract_cited_regulation_chunk_ids(answer: str, chunks: list[dict]) -> list[int]:
    citation_labels = re.findall(r"\[(C\d+)\]", answer)
    if not citation_labels:
        return []

    label_to_chunk_id = {
        chunk["citation_label"]: chunk["regulation_chunk_id"]
        for chunk in chunks
        if chunk.get("citation_label") and chunk.get("regulation_chunk_id") is not None
    }

    cited_regulation_chunk_ids: list[int] = []
    seen_chunk_ids: set[int] = set()
    for citation_label in citation_labels:
        regulation_chunk_id = label_to_chunk_id.get(citation_label)
        if regulation_chunk_id is None:
            continue
        if regulation_chunk_id in seen_chunk_ids:
            continue
        seen_chunk_ids.add(regulation_chunk_id)
        cited_regulation_chunk_ids.append(regulation_chunk_id)

    return cited_regulation_chunk_ids


def _resolve_source_url(chunks: list[dict], cited_regulation_chunk_ids: list[int]) -> str:
    if cited_regulation_chunk_ids:
        cited_chunk_id = cited_regulation_chunk_ids[0]
        for chunk in chunks:
            if chunk.get("regulation_chunk_id") == cited_chunk_id:
                return chunk.get("source_url", "") or ""
    return chunks[0].get("source_url", "") or ""
