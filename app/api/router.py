from fastapi import APIRouter

from app.api.admin_regulation_chunks import router as admin_regulation_chunks_router

api_router = APIRouter()
api_router.include_router(admin_regulation_chunks_router)
