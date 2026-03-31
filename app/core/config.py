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
    openai_api_key: Optional[str] = None


@lru_cache
def get_settings() -> Settings:
    # 호출 시점에 현재 환경을 읽어서 테스트나 스크립트에서 안전하게 덮어쓸 수 있게 합니다.
    app_env = os.getenv("APP_ENV", "dev")
    return Settings(
        _env_file=f".env.{app_env}",
        _env_file_encoding="utf-8",
    )


Settings.model_config = SettingsConfigDict(extra="ignore")
