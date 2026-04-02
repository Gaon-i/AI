"""관리자 라우터에서 공통으로 사용하는 간단한 토큰 인증 dependency입니다."""

from hmac import compare_digest
from typing import Optional

from fastapi import Header

from app.core.config import get_settings
from app.core.error_codes import ADMIN_API_TOKEN_INVALID
from app.core.error_codes import ADMIN_API_TOKEN_MISSING
from app.core.error_codes import UNAUTHORIZED
from app.core.exceptions import AppException


def require_admin_token(x_admin_token: Optional[str] = Header(default=None)) -> None:
    """X-Admin-Token 헤더를 검사해 관리자 API 접근을 허용할지 결정합니다.

    계약:
    - 헤더가 없으면 401
    - 헤더가 틀리면 403
    - 서버 설정이 없으면 500
    """

    settings = get_settings()
    if not settings.admin_api_token:
        raise AppException(ADMIN_API_TOKEN_MISSING)

    if x_admin_token is None:
        raise AppException(UNAUTHORIZED, detail="admin token required")

    if not compare_digest(x_admin_token, settings.admin_api_token):
        raise AppException(ADMIN_API_TOKEN_INVALID)
