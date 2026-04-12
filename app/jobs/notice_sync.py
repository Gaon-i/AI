"""공지사항 동기화 배치를 수동 실행하기 위한 진입점입니다."""

from datetime import datetime

from app.db.session import get_session_factory
from app.services.notice_sync_service import sync_recent_notices


def main() -> None:
    session = get_session_factory()()
    try:
        result = sync_recent_notices(
            db=session,
            now=datetime.now(),
        )
        print(result.model_dump_json())
    finally:
        session.close()


if __name__ == "__main__":
    main()
