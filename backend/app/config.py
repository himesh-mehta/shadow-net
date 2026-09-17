"""
Configuration management for SHADOW-NET using pydantic-settings.
Reads values from environment variables or .env file.
"""

from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # MongoDB
    MONGODB_URI: str = "mongodb://localhost:27017/shadow_net"
    MONGODB_DB_NAME: str = "shadow_net"

    # JWT Authentication
    JWT_SECRET: str = "shadow_net_insecure_development_secret_change_in_production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # Detection & Inference
    DETECTION_THRESHOLD: float = 0.75
    AUDIO_WINDOW_SECONDS: float = 2.0
    VAD_SENSITIVITY: int = 2
    DEMO_MODE: bool = True
    MODEL_PATH: str = "../model/resnet18.pth"

    # Audio Privacy Policy (Strictly False by default)
    STORE_AUDIO_DEFAULT: bool = False

    # Frontend CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
