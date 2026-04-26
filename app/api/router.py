from fastapi import APIRouter

from app.api.admin_chat import router as admin_chat_router
from app.api.admin_regulation_documents import router as admin_regulation_documents_router
from app.api.admin_regulation_chunk_ingestion import router as admin_regulation_chunk_ingestion_router
from app.api.regulations import router as regulations_router

api_router = APIRouter()
api_router.include_router(admin_chat_router)
api_router.include_router(admin_regulation_documents_router)
api_router.include_router(admin_regulation_chunk_ingestion_router)

# feat#6에서 추가

from app.api.chat import router as chat_router
from app.api.notice import router as notice_router

api_router.include_router(chat_router)
api_router.include_router(notice_router)
api_router.include_router(regulations_router)
