import os
from pathlib import Path


class Settings:
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "CHANGE_ME")
    DATABASE_URL: str = os.environ.get(
        "DATABASE_URL", "postgresql://chattr:chattrpass@localhost:5432/chattrdb"
    )
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 15)
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", 7))


settings = Settings()
