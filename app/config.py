"""
Configuration management using Pydantic Settings
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database
    DATABASE_URL: str
    
    # Gemini API
    GEMINI_API_KEY: str
    
    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    
    # Application
    APP_NAME: str = "Quiz Generation Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    
    # Quiz Settings
    DEFAULT_QUIZ_CACHE_TTL: int = 3600  # 1 hour
    MAX_QUIZ_QUESTIONS: int = 20
    MIN_COMPLETION_THRESHOLD: float = 0.75
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()