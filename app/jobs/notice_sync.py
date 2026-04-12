"""공지사항 동기화 배치를 수동 실행하기 위한 진입점입니다."""

from app.db.session import get_session_factory
from app.core.time_utils import get_current_kst_time
from app.services.notice_sync_service import sync_recent_notices


def main() -> None:
    session = get_session_factory()()
    try:
        result = sync_recent_notices(
            db=session,
            now=get_current_kst_time(),
        )
        print(result.model_dump_json())
    finally:
        session.close()


if __name__ == "__main__":
    main()
