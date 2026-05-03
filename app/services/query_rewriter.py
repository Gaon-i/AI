"""사용자 질문을 RAG 검색에 적합한 검색용 질의로 확장하는 서비스 파일입니다."""

from typing import Optional

from openai import OpenAI

from app.core.config import get_settings

settings = get_settings()
client = OpenAI(api_key=settings.openai_api_key)


def expand_query_for_retrieval(
    question: str,
    dormitory: Optional[str] = None,
) -> str:
    """
    원문 질문의 의미는 유지하면서 검색에 도움이 되는 키워드를 덧붙인 검색용 질의를 생성합니다.

    주의:
    - 답변 생성용 질문을 바꾸는 기능이 아닙니다.
    - pgvector 검색에만 사용할 검색용 텍스트를 만드는 기능입니다.
    - 실패하면 원문 질문을 그대로 반환합니다.
    """

    settings = get_settings()

    if not settings.chat_query_rewrite_enabled:
        return question

    normalized_question = question.strip()
    if not normalized_question:
        return question

    dormitory_text = dormitory or "생활관 미지정"

    prompt = f"""
너는 가천대학교 기숙사 챗봇의 RAG 검색 질의를 보강하는 도우미다.

목표:
사용자 질문의 의미를 바꾸지 말고, 벡터 검색에 도움이 되는 검색 키워드만 보강해라.

규칙:
1. 새로운 사실을 만들지 마라.
2. 사용자의 의도를 바꾸지 마라.
3. 답변을 작성하지 마라.
4. 검색용 문장만 출력해라.
5. 원문 질문을 반드시 포함해라.
6. 기숙사 관련 동의어, 시설명, 규정명, 유의어, 생활관 약칭을 추가할 수 있다.
7. 출력은 1~2문장으로 짧게 작성해라.
8. 불필요한 설명, 따옴표, 번호 목록은 출력하지 마라.

9. 사용자가 음료수, 물, 간식, 먹을 것, 마실 것, 살 곳, 사 먹을 곳, 구매할 곳을 물으면 편의점, 매점, 편의시설, 구매 위치 키워드를 포함해라.
10. 사용자가 방에서 라면, 조리, 끓여 먹기, 요리, 취사, 라면포트, 전기포트, 전열기구 사용 가능 여부를 물으면 반입금지 물품, 취사행위, 전열기구, 라면포트, 전기포트, 에어프라이어, 커피포트, 화재위험 키워드를 포함해라.
11. 사용자가 통금, 몇 시까지 들어가야 하는지, 문 닫는 시간, 새벽 출입, 출입 가능 시간을 물으면 폐문시간, 개문시간, 출입통제, 생활관 이용안내, 오전 1시, 오전 5시 키워드를 포함해라. 
단, 사용자가 휴게실을 직접 언급하지 않았다면 휴게실 통금보다 생활관 출입 통금으로 해석해라.
12.사용자가 "먹을 거", "간단하게 먹을 곳", "먹을거 해결", "사먹을 곳"처럼 식사/간식 해결 장소를 물으면 학생식당, 학식, 편의점, 매점, 배달음식 수령 키워드를 함께 포함해라.
13.사용자가 전자레인지, 음식 데우기, 데워먹기, 휴게실 전자레인지 위치를 물으면 휴게실, 공용시설, 전자레인지, 음식 데우기, 정수기, 싱크대 키워드를 포함해라.


예시:
사용자 질문: 새벽 2시에 들어가도 돼?
검색용 질의: 새벽 2시에 들어가도 돼? 검색 키워드: 폐문시간, 개문시간, 출입통제, 출입 가능 시간, 생활관 이용안내, 오전 1시, 오전 5시

사용자 질문: 음료수 살만한 곳 있어?
검색용 질의: 음료수 살만한 곳 있어? 검색 키워드: 편의점, 매점, 편의시설, 음료 구매, 간식 구매, 생활용품 구매 위치

사용자 질문: 방에서 라면 먹어도 돼?
검색용 질의: 방에서 라면 먹어도 돼? 검색 키워드: 호실 내 취사, 라면포트, 전열기구, 반입금지 물품, 취사 금지

사용자 질문: 방에서 라면 끓여 먹어도 돼?
검색용 질의: 방에서 라면 끓여 먹어도 돼? 검색 키워드: 호실 내 취사, 취사행위, 반입금지 물품, 전열기구, 라면포트, 전기포트, 화재위험

사용자 질문: 와이파이 비밀번호 뭐야?
검색용 질의: 와이파이 비밀번호 뭐야? 검색 키워드: 무선인터넷, 네트워크, wifi, 인터넷 비밀번호

사용자 질문: 음료수 사 먹을만한 곳 있어?
검색용 질의: 음료수 사 먹을만한 곳 있어? 검색 키워드: 편의점, 매점, 편의시설, 음료 구매, 간식 구매, 물 구매, 생활용품 구매 위치

사용자 질문: 기숙사 통금 시간 언제야?
검색용 질의: 기숙사 통금 시간 언제야? 검색 키워드: 폐문시간, 개문시간, 출입통제, 출입 가능 시간, 생활관 이용안내, 오전 1시, 오전 5시

사용자 질문: 통금 언제야?
검색용 질의: 통금 언제야? 검색 키워드: 폐문시간, 개문시간, 출입통제, 출입 가능 시간, 생활관 이용안내, 오전 1시, 오전 5시

사용자 질문: 전자레인지 어디있어?
검색용 질의: 전자레인지 어디있어? 검색 키워드: 휴게실, 공용시설, 전자레인지, 음식 데우기, 편의시설

사용자 질문: 음식 데워먹을 수 있어?
검색용 질의: 음식 데워먹을 수 있어? 검색 키워드: 휴게실, 공용시설, 전자레인지, 음식 데우기, 편의시설

사용자 생활관:
{dormitory_text}

사용자 질문:
{normalized_question}

검색용 질의:
"""

    try:
        response = client.chat.completions.create(
            model=settings.chat_query_rewrite_model,
            temperature=settings.chat_query_rewrite_temperature,
            messages=[
                {"role": "user", "content": prompt},
            ],
            timeout=settings.openai_timeout_seconds,
        )

        expanded_query = response.choices[0].message.content.strip()

        if not expanded_query:
            return normalized_question

        # 안전장치: LLM 결과에 원문 질문이 빠지면 원문을 앞에 붙인다.
        if normalized_question not in expanded_query:
            expanded_query = f"{normalized_question}\n검색 키워드: {expanded_query}"

        return expanded_query

    except Exception:
        # query expansion 실패가 챗봇 전체 실패로 이어지면 안 되므로 원문으로 fallback
        return normalized_question