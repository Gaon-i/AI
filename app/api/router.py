from fastapi import APIRouter

from app.api.admin_regulation_chunks import router as admin_regulation_chunks_router

api_router = APIRouter()
api_router.include_router(admin_regulation_chunks_router)

# feat#6에서 추가

from app.api.chat import router as chat_router
from app.api.notice import router as notice_router

api_router.include_router(chat_router)
api_router.include_router(notice_router)