from app.services import generator


def test_strip_citation_labels_removes_internal_labels() -> None:
    result = generator._strip_citation_labels(
        "외박 신청은 포털에서 하면 됩니다. [C2] 추가 확인은 규정을 보세요. [C1]"
    )

    assert result == "외박 신청은 포털에서 하면 됩니다. 추가 확인은 규정을 보세요."


def test_format_answer_with_source_appends_source_and_url() -> None:
    result = generator._format_answer_with_source(
        "택배는 생활관 호수까지 기입해 수령하면 됩니다.",
        source_chunk={
            "source": "실제 기숙사 거주생들의 팁",
            "source_url": "https://example.com/tips",
        },
        no_answer_message="관련 정보를 찾을 수 없습니다.",
    )

    assert result == (
        "택배는 생활관 호수까지 기입해 수령하면 됩니다.\n\n"
        "출처: 실제 기숙사 거주생들의 팁 (https://example.com/tips)"
    )


def test_format_answer_with_source_uses_source_without_url() -> None:
    result = generator._format_answer_with_source(
        "휴게실은 별도 통금 없이 이용할 수 있습니다.",
        source_chunk={
            "source": "실제 기숙사 거주생들의 팁",
            "source_url": None,
        },
        no_answer_message="관련 정보를 찾을 수 없습니다.",
    )

    assert result == (
        "휴게실은 별도 통금 없이 이용할 수 있습니다.\n\n"
        "출처: 실제 기숙사 거주생들의 팁"
    )


def test_format_answer_with_source_does_not_append_source_to_no_answer() -> None:
    result = generator._format_answer_with_source(
        "관련 정보를 찾을 수 없습니다.",
        source_chunk={
            "source": "생활관 규정집",
            "source_url": "https://example.com/rules",
        },
        no_answer_message="관련 정보를 찾을 수 없습니다.",
    )

    assert result == "관련 정보를 찾을 수 없습니다."


def test_resolve_source_url_returns_selected_source_chunk_url() -> None:
    result = generator._resolve_source_url(
        {"regulation_chunk_id": 16, "source_url": "https://example.com/1"}
    )

    assert result == "https://example.com/1"
