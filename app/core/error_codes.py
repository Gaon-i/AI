from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorCode:
    code: str
    message: str
    status: int


DATABASE_UNAVAILABLE = ErrorCode(
    code="DATABASE_UNAVAILABLE",
    message="database unavailable",
    status=503,
)
VALIDATION_ERROR = ErrorCode(
    code="VALIDATION_ERROR",
    message="request validation failed",
    status=422,
)
HTTP_ERROR = ErrorCode(
    code="HTTP_ERROR",
    message="http error",
    status=400,
)
INTERNAL_SERVER_ERROR = ErrorCode(
    code="INTERNAL_SERVER_ERROR",
    message="internal server error",
    status=500,
)

