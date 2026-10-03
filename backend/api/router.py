from fastapi import APIRouter

from api.routes import chat, conversations, documents, health, research, verification
from api.routes.sources import router as sources_router
from api.routes.evaluation import router as evaluation_router
from api.routes.providers import router as providers_router

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(research.router, prefix="/research", tags=["research"])
api_router.include_router(verification.router, prefix="/verify", tags=["verification"])
api_router.include_router(sources_router, prefix="/sources", tags=["sources"])
api_router.include_router(evaluation_router, prefix="/evaluation", tags=["evaluation"])
api_router.include_router(providers_router, prefix="/providers", tags=["providers"])
