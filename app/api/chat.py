from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.validator import validate_question
from app.services.embeddings import create_query_embedding
from app.services.generator import generate_answer
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