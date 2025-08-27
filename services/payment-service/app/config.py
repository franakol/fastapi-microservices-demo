"""
Configuration settings for Payment Service
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/payment_db"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # JWT
    jwt_secret: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    
    # Logging
    log_level: str = "INFO"
    
    # Payment processing
    payment_provider_url: str = "https://api.stripe.com"
    payment_provider_key: str = "sk_test_..."

    class Config:
        env_file = ".env"


settings = Settings()
