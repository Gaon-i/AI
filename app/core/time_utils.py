from datetime import datetime
from zoneinfo import ZoneInfo


def get_current_kst_time() -> datetime:
    """운영 기준 시각을 KST 기준 naive datetime으로 맞춥니다."""

    return datetime.now(ZoneInfo("Asia/Seoul")).replace(tzinfo=None)
