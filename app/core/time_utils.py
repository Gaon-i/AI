from datetime import datetime
from datetime import timezone
from zoneinfo import ZoneInfo


def get_current_kst_time() -> datetime:
    """운영 기준 시각을 KST 기준 naive datetime으로 맞춥니다."""

    return datetime.now(ZoneInfo("Asia/Seoul")).replace(tzinfo=None)


def get_current_utc_time() -> datetime:
    """서버 저장 기준 시각을 UTC 기준 naive datetime으로 맞춥니다."""

    return datetime.now(timezone.utc).replace(tzinfo=None)
