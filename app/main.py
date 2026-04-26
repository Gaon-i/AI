from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.router import api_router
from app.core.config import get_settings
from app.core.exception_handlers import add_exception_handlers


def create_app() -> FastAPI:
    # 앱 생성 시점의 설정을 사용해 실행 환경이 시작 단계에서 반영되도록 합니다.
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        summary="Gaon-i 생활관 AI 서버",
        description=(
            "Gaon-i 생활관 AI 서버의 기본 API 문서입니다.\n\n"
        ),
        contact={
            "name": "Gaon-i AI",
        },
        openapi_tags=[
            {
                "name": "health",
                "description": (
                    "서버와 데이터베이스 상태를 점검하는 API입니다. "
                    "배포 후 상태 확인, 로컬 개발 환경 점검, DB 연결 문제 확인에 사용합니다."
                ),
            },
            {
                "name": "admin-regulation-documents",
                "description": (
                    "관리자가 규정 원문 문서를 생성, 수정, 삭제하고 필요 시 rechunk를 수행할 때 사용하는 API입니다. "
                    "문서 버전 관리와 문서 상태 변경이 중심입니다."
                ),
            },
            {
                "name": "admin-regulation-chunk-ingestion",
                "description": (
                    "내부 운영/복구용 청크 적재 API입니다. 일반적인 문서 등록 흐름에서는 관리자가 직접 호출하지 않고, "
                    "`POST /api/v1/admin/regulations` 호출 시 서버 내부에서 자동 청킹과 임베딩 적재가 수행됩니다. "
                    "이 태그의 API는 문서 생성 후 자동 적재가 실패했거나, 문서는 존재하지만 청크가 비어 있는 예외 상황에서만 "
                    "수동 복구용으로 사용합니다. 기존 청크를 교체하는 작업은 이 태그가 아니라 문서 API의 `rechunk`를 사용합니다."
                ),
            },
        ],
    )

    add_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
