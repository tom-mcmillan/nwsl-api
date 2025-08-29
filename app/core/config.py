from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    PROJECT_NAME: str = "NWSL API"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    API_V1_STR: str = "/api/v1"
    
    # Database - use Cloud SQL Proxy or env vars
    # In production, Cloud Run connects via Unix socket
    DB_HOST: str = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT: int = int(os.getenv("DB_PORT", "5433"))
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "nwsl-api-2024")
    DB_NAME: str = os.getenv("DB_NAME", "nwsl_data")
    
    # Cloud SQL connection for production
    CLOUD_SQL_CONNECTION_NAME: str = os.getenv("CLOUD_SQL_CONNECTION_NAME", "")
    
    # Server
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # CORS - Update for production
    ALLOWED_ORIGINS: List[str] = [
        "https://nwsldata.com",
        "https://www.nwsldata.com",
        "http://localhost:3000",
        "http://localhost:8000"
    ]
    
    # API Key for basic authentication
    API_KEY_NAME: str = "X-API-Key"
    # In production, generate secure keys and store them properly
    DEMO_API_KEY: str = "nwsl-demo-key-2024"
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 100
    MAX_PAGE_SIZE: int = 1000
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()