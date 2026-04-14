from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.validator import validate_question
from app.services.embeddings import create_query_embedding
from app.services.generator import generate_answer, generate_grouped_answer
from app.repositories.regulation_chunk_repository import search_similar_chunks
from app.db.session import get_db

router = APIRouter(prefix="/ai/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    is_valid, normalized_question = validate_question(request.question)

    if not is_valid:
        return ChatResponse(
            answer="기숙사 관련 질문을 입력해주세요.",
            source_url=""
        )

    query_embedding = create_query_embedding(normalized_question)

    # dormitory가 있는 경우: 기존 방식 유지
    if request.dormitory:
        chunks = search_similar_chunks(
            db=db,
            query_embedding=query_embedding,
            dormitory=request.dormitory,
            top_k=3
        )

        answer, source_url = generate_answer(normalized_question, chunks)

        return ChatResponse(
            answer=answer,
            source_url=source_url or ""
        )

    # dormitory가 없는 경우: 생활관별로 각각 검색
    dormitories = ["제1학생생활관", "제2학생생활관", "제3학생생활관"]
    dormitory_chunks: dict[str, list[dict]] = {}

    for dormitory in dormitories:
        chunks = search_similar_chunks(
            db=db,
            query_embedding=query_embedding,
            dormitory=dormitory,
            top_k=2
        )
        dormitory_chunks[dormitory] = chunks

    answer, source_url = generate_grouped_answer(normalized_question, dormitory_chunks)

    return ChatResponse(
        answer=answer,
        source_url=source_url or ""
    )