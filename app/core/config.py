from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""

    # Application
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "ExpenseTracker"
    API_VERSION: str = "v1"

    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AWS S3
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET: str = "expense-tracker-receipts"
    S3_REGION: str = "us-east-1"
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_ENDPOINT_URL: str = ""  # For MinIO or custom S3-compatible storage

    # File Upload
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB
    ALLOWED_MIME_TYPES: str = "image/jpeg,image/png,image/gif,image/webp,application/pdf"

    # Celery
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # CORS (stored as string, parsed to list via property)
    CORS_ORIGINS_RAW: str = Field(default="http://localhost:3000", validation_alias="CORS_ORIGINS")

    # Logging
    LOG_LEVEL: str = "INFO"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    @property
    def CORS_ORIGINS(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS_RAW.split(",") if origin.strip()]

    @property
    def ALLOWED_MIME_TYPES_LIST(self) -> list[str]:
        """Parse comma-separated MIME types into a list."""
        return [
            mime_type.strip()
            for mime_type in self.ALLOWED_MIME_TYPES.split(",")
            if mime_type.strip()
        ]

    @property
    def api_prefix(self) -> str:
        """API prefix for versioning."""
        return f"/api/{self.API_VERSION}"


# Global settings instance
settings = Settings()
