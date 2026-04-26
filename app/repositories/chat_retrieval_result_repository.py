from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.chat_retrieval_result import ChatRetrievalResult


def create_chat_retrieval_results(
    db: Session,
    *,
    chat_log_id: int,
    retrieval_items: list[dict],
    retrieval_method: str,
) -> list[ChatRetrievalResult]:
    created_items: list[ChatRetrievalResult] = []
    seen_regulation_chunk_ids: set[int] = set()

    for rank, item in enumerate(retrieval_items, start=1):
        regulation_chunk_id = item.get("regulation_chunk_id")
        if regulation_chunk_id is None:
            continue
        if regulation_chunk_id in seen_regulation_chunk_ids:
            continue
        seen_regulation_chunk_ids.add(regulation_chunk_id)

        retrieval_result = ChatRetrievalResult(
            chat_log_id=chat_log_id,
            regulation_chunk_id=regulation_chunk_id,
            document_id=item.get("document_id"),
            document_version=item.get("document_version"),
            chunk_id=item.get("chunk_id"),
            retrieval_rank=rank,
            retrieval_score=item.get("similarity"),
            retrieval_method=retrieval_method,
            used_in_answer=False,
            selected_as_citation=False,
        )
        db.add(retrieval_result)
        created_items.append(retrieval_result)

    db.flush()
    return created_items


def mark_chat_retrieval_results_used_in_answer(
    db: Session,
    *,
    chat_log_id: int,
    cited_regulation_chunk_ids: list[int],
) -> list[ChatRetrievalResult]:
    statement = select(ChatRetrievalResult).where(ChatRetrievalResult.chat_log_id == chat_log_id)
    retrieval_results = list(db.execute(statement).scalars().all())
    citation_order_by_chunk_id = {
        regulation_chunk_id: order
        for order, regulation_chunk_id in enumerate(cited_regulation_chunk_ids, start=1)
    }

    for retrieval_result in retrieval_results:
        citation_order = citation_order_by_chunk_id.get(retrieval_result.regulation_chunk_id)
        retrieval_result.used_in_answer = citation_order is not None
        retrieval_result.selected_as_citation = citation_order is not None
        retrieval_result.citation_order = citation_order

    db.flush()
    return retrieval_results
