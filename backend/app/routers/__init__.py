from app.routers.auth import router as auth_router
from app.routers.sessions import router as sessions_router
from app.routers.settings import router as settings_router
from app.routers.incidents import router as incidents_router
from app.routers.audio import router as audio_router

__all__ = [
    "auth_router",
    "sessions_router",
    "settings_router",
    "incidents_router",
    "audio_router",
]
