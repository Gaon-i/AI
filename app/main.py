from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    # 앱 생성 시점의 설정을 사용해 실행 환경이 시작 단계에서 반영되도록 합니다.
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
    )

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/health", tags=["health"])
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
