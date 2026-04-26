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
    for retrieval_result in created_items:
        db.refresh(retrieval_result)
    return created_items


def mark_chat_retrieval_results_used_in_answer(
    db: Session,
    *,
    chat_log_id: int,
) -> list[ChatRetrievalResult]:
    statement = select(ChatRetrievalResult).where(ChatRetrievalResult.chat_log_id == chat_log_id)
    retrieval_results = list(db.execute(statement).scalars().all())

    for retrieval_result in retrieval_results:
        retrieval_result.used_in_answer = True

    db.flush()
    for retrieval_result in retrieval_results:
        db.refresh(retrieval_result)
    return retrieval_results
