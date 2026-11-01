from app.routers.auth import router as auth_router
from app.routers.sessions import router as sessions_router
from app.routers.settings import router as settings_router
from app.routers.incidents import router as incidents_router
from app.routers.audio import router as audio_router
from app.routers.ws import router as ws_router
from app.routers.verify import router as verify_router
from app.routers.analytics import router as analytics_router
from app.routers.evaluation import router as evaluation_router

__all__ = [
    "auth_router",
    "sessions_router",
    "settings_router",
    "incidents_router",
    "audio_router",
    "ws_router",
    "verify_router",
    "analytics_router",
    "evaluation_router",
]
