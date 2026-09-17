"""
SHADOW-NET Backend Service
Controlled Deepfake Voice Detection & Interception Prototype

DISCLAIMER:
This prototype operates exclusively in controlled, self-owned test environments.
It does NOT intercept real third-party VoIP, Zoom, Microsoft Teams, or PSTN calls.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import connect_to_mongo, close_mongo_connection
from app.routers import (
    auth_router,
    sessions_router,
    settings_router,
    incidents_router,
    audio_router,
    ws_router,
    verify_router,
    analytics_router,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("shadow_net")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown events."""
    logger.info("Starting SHADOW-NET backend service...")
    await connect_to_mongo()
    yield
    logger.info("Shutting down SHADOW-NET backend service...")
    await close_mongo_connection()


app = FastAPI(
    title="SHADOW-NET API",
    description="Real-time Deepfake Voice Interception & Analysis Prototype (Controlled Test Environment)",
    version="0.4.0",
    lifespan=lifespan,
)

settings = get_settings()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(sessions_router)
app.include_router(settings_router)
app.include_router(incidents_router)
app.include_router(audio_router)
app.include_router(ws_router)
app.include_router(verify_router)
app.include_router(analytics_router)


@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint verifying API and DB connectivity.
    """
    from app.db import db_manager

    db_status = "connected" if db_manager.db is not None else "disconnected"
    db_mode = "mock" if db_manager.is_mock else "mongodb"

    return {
        "status": "ok",
        "service": "shadow-net-backend",
        "version": "0.4.0",
        "database": {
            "status": db_status,
            "engine": db_mode,
        },
        "environment": "development",
    }


@app.get("/", tags=["System"])
async def root():
    return {
        "name": "SHADOW-NET Prototype API",
        "status": "operational",
        "disclaimer": "Controlled test environment only. No third-party VoIP interception.",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
