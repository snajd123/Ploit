"""
Configuration management for Poker Analysis App.

All configuration values are loaded from environment variables.
Use .env file for local development and environment variables for production.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All values can be set via .env file or system environment variables.
    """

    # Database Configuration
    database_url: str
    database_pool_size: int = 2  # Reduced for Supabase Session mode limits
    database_pool_max_overflow: int = 1  # Very limited overflow

    # Claude API
    anthropic_api_key: str

    # Backend Server
    backend_port: int = 8000
    backend_host: str = "0.0.0.0"
    backend_workers: int = 1  # Single worker for Supabase Session mode limits

    # Frontend URL (for CORS)
    frontend_url: str = "http://localhost:3000"

    # Environment
    environment: str = "development"
    log_level: str = "INFO"

    # Security
    secret_key: str
    allowed_origins: str = "http://localhost:3000"

    class Config:
        """Pydantic configuration"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse comma-separated allowed origins into list"""
        return [origin.strip() for origin in self.allowed_origins.split(',')]

    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment.lower() == "production"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses LRU cache to avoid re-reading environment variables on every call.

    Returns:
        Settings instance with all configuration values
    """
    return Settings()
