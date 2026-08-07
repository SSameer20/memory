from fastapi import APIRouter

from .document import router as document_router

api_router = APIRouter()

api_router.include_router(document_router)
 