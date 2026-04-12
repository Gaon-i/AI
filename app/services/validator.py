def validate_question(question: str) -> tuple[bool, str]:
    """
    질문이 기숙사 관련인지 간단하게 검증하고
    정규화된 질문을 반환
    """

    if not question or len(question.strip()) < 2:
        return False, "질문이 너무 짧습니다."

    # 기본 정규화
    normalized = question.strip()

    # (지금은 단순 검증, 나중에 LLM 붙일 수 있음)
    return True, normalized