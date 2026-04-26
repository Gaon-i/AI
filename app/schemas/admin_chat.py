from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AdminChatLogDetail(BaseModel):
    chat_log_id: int
    session_id: str
    user_id: Optional[int] = None
    question: str
    rewritten_query: Optional[str] = None
    answer: Optional[str] = None
    answer_status: str
    model_name: Optional[str] = None
    prompt_version: Optional[str] = None
    retrieval_version: Optional[str] = None
    response_time: Optional[int] = None
    created_at: datetime
    retrieval_results: list["AdminChatRetrievalResult"] = []


class AdminChatRetrievalResult(BaseModel):
    chat_retrieval_result_id: int
    regulation_chunk_id: int
    document_id: Optional[str] = None
    document_version: Optional[str] = None
    chunk_id: Optional[str] = None
    retrieval_rank: Optional[int] = None
    retrieval_score: Optional[float] = None
    rerank_score: Optional[float] = None
    retrieval_method: Optional[str] = None
    used_in_answer: bool
    selected_as_citation: bool
    citation_order: Optional[int] = None
    created_at: datetime


class AdminChatSessionSummary(BaseModel):
    session_id: str
    user_id: Optional[int] = None
    total_turns: int
    started_at: datetime
    last_activity_at: datetime
    is_expired: bool


class AdminRecentChatSessionsResult(BaseModel):
    items: list[AdminChatSessionSummary]
