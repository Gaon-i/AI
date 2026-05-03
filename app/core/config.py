import os
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 환경별 env 파일에서 읽어오는 애플리케이션 공통 설정입니다.
    app_env: str = "dev"
    app_name: str = "gaon-i-ai"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/gaon_i"
    admin_api_token: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimension: int = 1536
    openai_timeout_seconds: float = 10.0
    chat_answer_model: str = "gpt-4o-mini"
    notice_summary_model: str = "gpt-4o-mini"
    chat_prompt_version_single: str = "chat-answer-source-v1"
    chat_prompt_version_grouped: str = "chat-answer-unspecified-dormitory-source-v1"
    chat_retrieval_version_single: str = "hybrid-dormitory-search-v1"
    chat_retrieval_version_grouped: str = "hybrid-dormitory-search-unspecified-v1"
    chat_retrieval_method_single: str = "hybrid_dormitory_top_k"
    chat_retrieval_method_grouped: str = "hybrid_unspecified_dormitory_top_k"
    chat_no_answer_message: str = "관련 정보를 찾을 수 없습니다."
    chat_invalid_question_message: str = "기숙사 관련 질문을 입력해주세요."
    chat_single_dormitory_top_k: int = 3
    chat_grouped_dormitory_top_k: int = 2
    chat_grouped_dormitories: list[str] = ["제1학생생활관", "제2학생생활관", "제3학생생활관"]
    regulation_chunk_max_length: int = 400
    chat_session_timeout_minutes: int = 30

    chat_fallback_top_k: int = 5
    chat_retrieval_method_fallback: str = "hybrid_all_dormitories_fallback"
    chat_retrieval_version_fallback: str = "hybrid-dormitory-search-fallback-v1"

    chat_fallback_similarity_threshold: float = 0.35

    chat_query_rewrite_enabled: bool = True
    chat_query_rewrite_model: str = "gpt-4o-mini"
    chat_query_rewrite_temperature: float = 0.0
    chat_retrieval_method_query_expansion: str = "vector_query_expansion_fallback"
    chat_retrieval_version_query_expansion: str = "query-expansion-fallback-v1"


@lru_cache
def get_settings() -> Settings:
    # 호출 시점에 현재 환경을 읽어서 테스트나 스크립트에서 안전하게 덮어쓸 수 있게 합니다.
    app_env = os.getenv("APP_ENV", "dev")
    return Settings(
        _env_file=f".env.{app_env}",
        _env_file_encoding="utf-8",
    )


Settings.model_config = SettingsConfigDict(extra="ignore")
