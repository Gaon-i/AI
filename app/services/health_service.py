from sqlalchemy.orm import Session

from app.core.error_codes import DATABASE_UNAVAILABLE
from app.core.exceptions import AppException
from app.repositories.health_repository import check_connection
from app.schemas.common import ApiResponse
from app.schemas.common import HealthResponseData


def get_health_response() -> ApiResponse[HealthResponseData]:
    return ApiResponse(
        status=200,
        message="success",
        data=HealthResponseData(status="ok"),
    )


def get_db_health_response(db: Session) -> ApiResponse[HealthResponseData]:
    try:
        check_connection(db)
    except Exception as exc:  # pragma: no cover - exercised by real environment checks
        raise AppException(DATABASE_UNAVAILABLE) from exc

    return get_health_response()
