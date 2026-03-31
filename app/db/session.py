from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def get_db() -> Generator[Session, None, None]:
    # 요청 단위로 세션을 열고 닫아 DB 사용 범위를 명확하게 유지합니다.
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()


@lru_cache
def get_engine() -> Engine:
    # 실제 사용 시점에 엔진을 만들어 환경 변경이 첫 연결 전에 반영되도록 합니다.
    settings = get_settings()
    return create_engine(settings.database_url, future=True)


@lru_cache
def get_session_factory() -> sessionmaker:
    # 현재 엔진을 기준으로 세션 팩토리를 캐시해 같은 프로세스에서 재사용합니다.
    return sessionmaker(bind=get_engine(), autocommit=False, autoflush=False, class_=Session)


def check_db_connection() -> None:
    # 가장 가벼운 쿼리로 연결만 확인해서 헬스체크 부담을 줄입니다.
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))
