import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    APP_NAME: str = "AquaSmart AI — Telemetry & Feeding Optimizer"
    API_V1_STR: str = "/api"
    SECRET_KEY: str = "aquasmart-super-secret-key-for-jwt-signing-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    DATABASE_URL: str = "sqlite:///./aquasmart.db"
    DEMO_MODE_DEFAULT: bool = True
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    MAX_UPLOAD_SIZE_MB: int = 10
    STALE_DATA_TIMEOUT_MINUTES: int = 15

settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
