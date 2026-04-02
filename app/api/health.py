from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.common import HealthResponseData
from app.services.health_service import get_db_health_response
from app.services.health_service import get_health_response

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=ApiResponse[HealthResponseData],
    summary="애플리케이션 헬스체크",
    description=(
        "FastAPI 애플리케이션 프로세스가 정상적으로 실행 중인지 확인합니다. "
        "서버 자체가 살아 있는지만 빠르게 확인할 때 사용합니다."
    ),
    response_description="애플리케이션이 정상 실행 중이면 status=ok를 반환합니다.",
)
def health_check() -> ApiResponse[HealthResponseData]:
    return get_health_response()


@router.get(
    "/health/db",
    response_model=ApiResponse[HealthResponseData],
    summary="데이터베이스 헬스체크",
    description=(
        "애플리케이션이 PostgreSQL 데이터베이스에 실제로 연결 가능한지 확인합니다. "
        "DB 접속 정보가 맞는지, PostgreSQL이 실행 중인지, 네트워크 연결에 문제가 없는지 점검할 때 사용합니다."
    ),
    response_description="DB 연결이 가능하면 status=ok를 반환합니다.",
    responses={
        503: {
            "description": "데이터베이스 연결에 실패한 경우 반환됩니다.",
        }
    },
)
def db_health_check(db: Session = Depends(get_db)) -> ApiResponse[HealthResponseData]:
    return get_db_health_response(db)
