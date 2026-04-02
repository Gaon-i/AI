"""애플리케이션 전반에서 공통으로 사용하는 에러 코드를 모아둔 파일입니다."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorCode:
    """HTTP status와 내부 에러 코드를 함께 다루기 위한 공통 에러 모델입니다."""

    code: str
    message: str
    status: int


BAD_REQUEST = ErrorCode(
    code="BAD_REQUEST",
    message="bad request",
    status=400,
)
UNAUTHORIZED = ErrorCode(
    code="UNAUTHORIZED",
    message="authentication required",
    status=401,
)
FORBIDDEN = ErrorCode(
    code="FORBIDDEN",
    message="forbidden",
    status=403,
)
NOT_FOUND = ErrorCode(
    code="NOT_FOUND",
    message="resource not found",
    status=404,
)
METHOD_NOT_ALLOWED = ErrorCode(
    code="METHOD_NOT_ALLOWED",
    message="method not allowed",
    status=405,
)
CONFLICT = ErrorCode(
    code="CONFLICT",
    message="resource conflict",
    status=409,
)
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
RATE_LIMITED = ErrorCode(
    code="RATE_LIMITED",
    message="too many requests",
    status=429,
)
INTERNAL_SERVER_ERROR = ErrorCode(
    code="INTERNAL_SERVER_ERROR",
    message="internal server error",
    status=500,
)
EXTERNAL_API_ERROR = ErrorCode(
    code="EXTERNAL_API_ERROR",
    message="external api error",
    status=502,
)
OPENAI_API_ERROR = ErrorCode(
    code="OPENAI_API_ERROR",
    message="openai api error",
    status=502,
)
OPENAI_API_KEY_MISSING = ErrorCode(
    code="OPENAI_API_KEY_MISSING",
    message="openai api key is missing",
    status=500,
)
OPENAI_API_TIMEOUT = ErrorCode(
    code="OPENAI_API_TIMEOUT",
    message="openai api timeout",
    status=504,
)
EMBEDDING_GENERATION_FAILED = ErrorCode(
    code="EMBEDDING_GENERATION_FAILED",
    message="failed to generate embedding",
    status=502,
)
EMBEDDING_DIMENSION_MISMATCH = ErrorCode(
    code="EMBEDDING_DIMENSION_MISMATCH",
    message="embedding dimension mismatch",
    status=500,
)
INVALID_EMBEDDING_RESPONSE = ErrorCode(
    code="INVALID_EMBEDDING_RESPONSE",
    message="invalid embedding response",
    status=502,
)
INVALID_CHUNK_TEXT = ErrorCode(
    code="INVALID_CHUNK_TEXT",
    message="invalid chunk text",
    status=400,
)
REGULATION_CHUNK_NOT_FOUND = ErrorCode(
    code="REGULATION_CHUNK_NOT_FOUND",
    message="regulation chunk not found",
    status=404,
)
REGULATION_CHUNK_ALREADY_EXISTS = ErrorCode(
    code="REGULATION_CHUNK_ALREADY_EXISTS",
    message="regulation chunk already exists",
    status=409,
)
REGULATION_CHUNK_CREATE_FAILED = ErrorCode(
    code="REGULATION_CHUNK_CREATE_FAILED",
    message="failed to create regulation chunk",
    status=500,
)
REGULATION_CHUNK_UPDATE_FAILED = ErrorCode(
    code="REGULATION_CHUNK_UPDATE_FAILED",
    message="failed to update regulation chunk",
    status=500,
)
REGULATION_CHUNK_DELETE_FAILED = ErrorCode(
    code="REGULATION_CHUNK_DELETE_FAILED",
    message="failed to delete regulation chunk",
    status=500,
)
REGULATION_CHUNK_BULK_CREATE_FAILED = ErrorCode(
    code="REGULATION_CHUNK_BULK_CREATE_FAILED",
    message="failed to create regulation chunks",
    status=500,
)
