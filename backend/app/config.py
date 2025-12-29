"""Configuration management"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):  # type: ignore[misc]
    """Application settings"""

    model_config = SettingsConfigDict(env_file=".env")

    # Database
    database_url: str = "sqlite:///./data/history.db"

    # Meilisearch
    meilisearch_url: str = "http://localhost:7700"
    meilisearch_master_key: str = ""

    # Admin bootstrap
    admin_username: str = ""
    admin_email: str = ""
    admin_password: str = ""

    # Session security
    secret_key: str = ""  # Required - must be set via environment variable
    session_expire_hours: int = 24

    # Email/SMTP configuration
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@example.com"
    smtp_use_tls: bool = True

    # CORS configuration
    cors_origins: str = ""  # Comma-separated list of allowed origins, empty = no CORS
    cors_allow_credentials: bool = False

    # Security
    secure_cookies: bool = False  # Set to True in production with HTTPS
    environment: str = "development"  # development, production


settings = Settings()
