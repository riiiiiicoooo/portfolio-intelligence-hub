"""Application configuration."""

from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration from environment variables."""

    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_BASE_URL: str = "http://localhost:8000"
    APP_BASE_URL: str = "http://localhost:3000"
    
    # Clerk Auth
    CLERK_API_KEY: str
    CLERK_API_ID: str
    CLERK_API_URL: str = "https://api.clerk.com"
    
    # Database
    DATABASE_URL: str
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # Snowflake
    SNOWFLAKE_ACCOUNT: str
    SNOWFLAKE_USER: str
    SNOWFLAKE_PASSWORD: str
    SNOWFLAKE_DATABASE: str
    SNOWFLAKE_SCHEMA: str = "public"
    SNOWFLAKE_WAREHOUSE: str = "compute"
    
    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # Supabase (for vector DB)
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_KEY: str
    
    # Trigger.dev
    TRIGGER_API_KEY: str
    
    # AWS S3 (for document storage)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_S3_BUCKET: str = "portfolio-hub-documents"
    AWS_S3_REGION: str = "us-east-1"
    
    # Email
    RESEND_API_KEY: str
    ALERT_EMAIL: str = "alerts@portfoliointelligence.hub"
    
    # Slack
    SLACK_WEBHOOK_ID: Optional[str] = None
    
    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://app.portfoliointelligence.hub",
    ]
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = True
