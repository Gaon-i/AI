from datetime import datetime
from typing import Literal
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    question: str
    dormitory: Optional[str] = None


class ChatResponse(BaseModel):
    chat_log_id: int
    session_id: str
    answer: str
    answer_status: str
    source_url: str


ChatFeedbackReasonCode = Literal[
    "INCORRECT_ANSWER",
    "BAD_CITATION",
    "TOO_LONG",
    "TOO_VAGUE",
    "OUTDATED_INFO",
    "NO_SOURCE",
    "OTHER",
]


class ChatFeedbackCreateRequest(BaseModel):
    chat_log_id: int = Field(ge=1)
    is_helpful: bool
    reason_code: Optional[ChatFeedbackReasonCode] = Field(
        default=None,
        description=(
            "불만족 사유 코드입니다. "
            "INCORRECT_ANSWER=답변이 질문과 다르거나 틀림, "
            "BAD_CITATION=근거/출처가 부정확함, "
            "TOO_LONG=답변이 너무 김, "
            "TOO_VAGUE=답변이 모호함, "
            "OUTDATED_INFO=정보가 오래됨, "
            "NO_SOURCE=출처가 없음, "
            "OTHER=기타"
        ),
    )
    feedback_comment: Optional[str] = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_negative_feedback_fields(self) -> "ChatFeedbackCreateRequest":
        if self.is_helpful and (self.reason_code is not None or self.feedback_comment is not None):
            raise ValueError("reason_code and feedback_comment should only be provided for negative feedback.")
        return self


class ChatFeedbackCreateResponse(BaseModel):
    feedback_id: int
    chat_log_id: int
    is_helpful: bool
    feedback_type: Literal["LIKE", "DISLIKE", "RATING"]
    reason_code: Optional[ChatFeedbackReasonCode] = None
    feedback_comment: Optional[str] = None
    created_at: datetime


class ChatSessionCreateRequest(BaseModel):
    user_id: Optional[int] = Field(default=None, ge=1)


class ChatSessionCreateResponse(BaseModel):
    session_id: str
    user_id: Optional[int] = None
    total_turns: int
    started_at: datetime
    ended_at: Optional[datetime] = None
    last_activity_at: datetime
    created_at: datetime
