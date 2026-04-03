from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "PulseChat"
    APP_ENV: str = "development"
    SECRET_KEY: str = "change-this-secret-key-in-production-min-32-chars"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    DATABASE_URL: str = "postgresql+asyncpg://pulsechat:pulsechat_pass@postgres:5432/pulsechat"
    SYNC_DATABASE_URL: str = "postgresql://pulsechat:pulsechat_pass@postgres:5432/pulsechat"

    REDIS_URL: str = "redis://redis:6379/0"

    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000", "http://frontend:80"]

    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 50
    OTP_EXPIRE_MINUTES: int = 10
    ALGORITHM: str = "HS256"

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@pulsechat.app"

    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    FRONTEND_URL: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
