from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Google OAuth
    google_client_id: str
    google_client_secret: str
    google_ads_developer_token: str

    # Groq (Llama 3.3)
    groq_api_key: str

    # Database
    database_url: str
    supabase_url: str = ""
    supabase_key: str = ""

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"

    # App
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"
    secret_key: str

    # Encryption key for storing refresh tokens (32-byte Fernet key, base64-encoded)
    encryption_key: str

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
