from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/kistrader"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # KIS API
    KIS_BASE_URL: str = "https://openapi.koreainvestment.com:9443"
    KIS_ENCRYPT_KEY: str = "change-me-32-bytes-fernet-key-here"

    # Slack
    SLACK_BOT_TOKEN: str = ""
    SLACK_CHANNEL: str = "#kis-trader"
    SLACK_WEBHOOK_URL: str = ""

    # Backtest Worker
    BACKTEST_WORKER_URL: str = "http://localhost:8001"

    # Real Trading (internal)
    REAL_TRADING_URL: str = "http://localhost:8002"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "https://trade.yourdomain.com"]

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
