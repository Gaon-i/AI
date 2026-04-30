from datetime import date
from datetime import datetime
from typing import Literal
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


AdminChatReviewQueueReason = Literal["ERROR", "NO_ANSWER", "NEGATIVE_FEEDBACK"]


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
    retrieval_results: list["AdminChatRetrievalResult"] = Field(default_factory=list)
    error_logs: list["AdminChatErrorLog"] = Field(default_factory=list)
    feedbacks: list["AdminChatFeedback"] = Field(default_factory=list)
    admin_reviews: list["AdminChatAdminReview"] = Field(default_factory=list)


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


class AdminChatErrorLog(BaseModel):
    error_id: int
    error_type: str
    error_message: str
    error_detail: Optional[str] = None
    occurred_step: Optional[str] = None
    created_at: datetime


class AdminChatFeedback(BaseModel):
    feedback_id: int
    user_id: Optional[int] = None
    feedback_type: str
    is_helpful: Optional[bool] = None
    rating: Optional[int] = None
    reason_code: Optional[str] = None
    feedback_comment: Optional[str] = None
    feature_type: Optional[str] = None
    created_at: datetime


class AdminChatAdminReview(BaseModel):
    review_id: int
    admin_id: int
    correctness_label: str
    citation_label: Optional[str] = None
    root_cause: Optional[str] = None
    correction_required: bool
    corrected_answer: Optional[str] = None
    review_note: Optional[str] = None
    created_at: datetime


class AdminChatSessionSummary(BaseModel):
    session_id: str
    user_id: Optional[int] = None
    total_turns: int
    started_at: datetime
    ended_at: Optional[datetime] = None
    last_activity_at: datetime
    created_at: datetime
    is_expired: bool


class AdminChatSessionsByDateResult(BaseModel):
    date: date
    page: int
    size: int
    total_count: int
    items: list[AdminChatSessionSummary]


class AdminChatReviewQueueItem(BaseModel):
    chat_log_id: int
    session_id: str
    user_id: Optional[int] = None
    question: str
    answer_preview: Optional[str] = None
    answer_status: str
    review_reason: AdminChatReviewQueueReason
    negative_feedback_count: int
    latest_feedback_reason_code: Optional[str] = None
    created_at: datetime


class AdminChatReviewQueueResult(BaseModel):
    page: int
    size: int
    total_count: int
    total_pages: int
    items: list[AdminChatReviewQueueItem]
