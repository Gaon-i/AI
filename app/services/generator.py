import json
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
참고 정보에 없는 일반 상식이나 추측으로 답하지 마라.
"일반적으로", "가능성이 높습니다", "가능할 수 있습니다", "허용되지 않을 것으로 보입니다", "확인하는 것이 좋습니다"처럼 근거 없는 추측 표현을 사용하지 마라.
사용자가 "방에서 라면 먹어도 돼?"처럼 질문한 경우, 참고 정보에 방 안 취식 금지 규정이 없으면 라면을 먹는 행위 자체를 금지한다고 단정하지 마라.
다만 참고 정보에 라면포트, 전기포트, 전열기구, 취사행위 금지 내용이 있으면 "방에서 라면을 조리해 먹는 것은 허용되지 않는다"라고 안내해라.
질문에서 생활관을 특정하지 않았고 참고 정보가 특정 생활관에만 해당하면, 해당 생활관 기준 답변임을 명확히 밝혀라.
질문에서 생활관을 특정하지 않았더라도 생활관별 구분을 강제로 만들지 말고, 가장 관련 있는 정보 중심으로 간결하게 답변해라.
참고 정보에 생활관 구분이 없거나 공통 규정으로 보이면 일반 답변으로 안내해라.
{fallback_instruction}

반드시 아래 JSON 형식으로만 출력해라.
설명 문장, 마크다운, 코드블록은 출력하지 마라.

형식:
{{
  "answer": "사용자에게 보여줄 최종 답변",
  "used_reference_index": 1
}}

규칙:
- "answer"에는 답변 본문만 작성해라.
- "answer"에는 출처 문구를 넣지 마라.
- "used_reference_index"에는 답변 작성에 가장 직접적으로 사용한 참고 정보 번호를 넣어라.
- 여러 참고 정보를 사용했다면 가장 핵심 근거가 되는 참고 정보 번호 하나만 넣어라.
- 질문에 답할 정보가 충분하지 않으면 "answer"는 정확히 "{settings.chat_no_answer_message}"로 작성하고, "used_reference_index"는 null로 작성해라.
- 참고 정보 번호는 [참고 정보 1], [참고 정보 2]의 숫자를 기준으로 한다.

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

    raw_output = response.choices[0].message.content.strip()
    parsed_answer, used_reference_index = _parse_generation_output(
        raw_output,
        no_answer_message=settings.chat_no_answer_message,
    )

    answer_without_labels = _strip_citation_labels(parsed_answer)
    source_chunk = _select_source_chunk_by_reference_index(
        chunks,
        used_reference_index,
    )

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


def _parse_generation_output(
    raw_output: str,
    *,
    no_answer_message: str,
) -> tuple[str, Optional[int]]:
    try:
        payload = json.loads(_strip_json_code_block(raw_output))
    except json.JSONDecodeError:
        # 혹시 모델이 JSON 형식을 어기면 기존 방식처럼 전체 텍스트를 답변으로 사용
        return raw_output.strip(), None

    if not isinstance(payload, dict):
        return no_answer_message, None

    answer = payload.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        return no_answer_message, None

    used_reference_index = payload.get("used_reference_index")
    if used_reference_index is None:
        return answer.strip(), None

    if isinstance(used_reference_index, int):
        return answer.strip(), used_reference_index

    return answer.strip(), None


def _strip_json_code_block(raw_output: str) -> str:
    text = raw_output.strip()

    # LLM이 ```json ... ``` 코드블록으로 감싼 경우 우선 제거
    if text.startswith("```json"):
        text = text.removeprefix("```json").strip()
    elif text.startswith("```"):
        text = text.removeprefix("```").strip()

    if text.endswith("```"):
        text = text.removesuffix("```").strip()

    # 앞뒤 설명이 섞여도 JSON 객체 부분만 추출
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0).strip()

    return text


def _select_source_chunk_by_reference_index(
    chunks: list[dict],
    used_reference_index: Optional[int],
) -> Optional[dict]:
    if not chunks:
        return None

    if used_reference_index is None:
        return None

    chunk_index = used_reference_index - 1
    if chunk_index < 0 or chunk_index >= len(chunks):
        return None

    return chunks[chunk_index]
