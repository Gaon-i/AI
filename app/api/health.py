from fastapi import APIRouter
from fastapi import HTTPException

from app.db.session import check_db_connection

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/db")
def db_health_check() -> dict[str, str]:
    try:
        check_db_connection()
    except Exception as exc:  # pragma: no cover - exercised by real environment checks
        raise HTTPException(status_code=503, detail="database unavailable") from exc

    return {"status": "ok"}
