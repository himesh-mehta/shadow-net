"""
SHADOW-NET Backend Service
Controlled Deepfake Voice Detection & Interception Prototype

DISCLAIMER:
This prototype operates exclusively in controlled, self-owned test environments.
It does NOT intercept real third-party VoIP, Zoom, Microsoft Teams, or PSTN calls.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="SHADOW-NET API",
    description="Real-time Deepfake Voice Interception & Analysis Prototype",
    version="0.1.0",
)

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint for container probes and platform monitoring.
    """
    return {
        "status": "ok",
        "service": "shadow-net-backend",
        "version": "0.1.0",
        "environment": "development",
    }


@app.get("/", tags=["System"])
async def root():
    return {
        "name": "SHADOW-NET Prototype API",
        "status": "operational",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
