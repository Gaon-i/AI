from app.services import generator


def test_extract_cited_regulation_chunk_ids_returns_unique_ids_in_order() -> None:
    chunks = [
        {"citation_label": "C1", "regulation_chunk_id": 16, "source_url": "https://example.com/1"},
        {"citation_label": "C2", "regulation_chunk_id": 13, "source_url": "https://example.com/2"},
    ]

    result = generator._extract_cited_regulation_chunk_ids(
        "외박 신청은 포털에서 하면 됩니다. [C2] 추가 확인은 규정을 보세요. [C1] 다시 참고 [C2]",
        chunks,
    )

    assert result == [13, 16]


def test_resolve_source_url_prefers_first_cited_chunk() -> None:
    chunks = [
        {"citation_label": "C1", "regulation_chunk_id": 16, "source_url": "https://example.com/1"},
        {"citation_label": "C2", "regulation_chunk_id": 13, "source_url": "https://example.com/2"},
    ]

    result = generator._resolve_source_url(chunks, [13])

    assert result == "https://example.com/2"
