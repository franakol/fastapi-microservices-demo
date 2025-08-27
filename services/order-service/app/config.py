"""
Configuration settings for Order Service
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/order_db"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # JWT
    jwt_secret: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    
    # Logging
    log_level: str = "INFO"
    
    # Service URLs
    user_service_url: str = "http://user-service:8000"
    payment_service_url: str = "http://payment-service:8000"

    class Config:
        env_file = ".env"


settings = Settings()
