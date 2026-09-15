from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings loaded from environment and .env file."""
    
    app_env: str = "development"
    app_port: int = 8000
    
    # Database
    database_url: str = "postgresql://postgres:Doremon@123@localhost:5432/webhook_engine"
    
    # Redis & Broker
    redis_url: str = "redis://localhost:6379/0"
    
    # Webhook Engine Retry & Timeout Config
    max_retries: int = 3
    retry_base_delay: int = 2
    request_timeout: int = 5
    
    # Security
    webhook_secret: str = "super_secret_webhook_signing_key_32bytes_min"
    
    # Default Receiver URL
    default_receiver_url: str = "http://127.0.0.1:9000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance to avoid re-reading disk repeatedly."""
    return Settings()


settings = get_settings()
