from typing import Optional

from app.core.error_codes import ErrorCode


class AppException(Exception):
    def __init__(self, error_code: ErrorCode, detail: Optional[str] = None) -> None:
        self.error_code = error_code
        self.detail = detail or error_code.message
        super().__init__(self.detail)

