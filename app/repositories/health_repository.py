from sqlalchemy import text
from sqlalchemy.orm import Session


def check_connection(db: Session) -> None:
    # 가장 가벼운 쿼리로 DB 연결 가능 여부만 확인합니다.
    db.execute(text("SELECT 1"))
