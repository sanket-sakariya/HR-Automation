from __future__ import annotations
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


# Determine project root (where .env file should be located)
# This file is at: app/config/baseapp_config.py
# Project root is 2 levels up
_project_root = Path(__file__).parent.parent.parent
_env_file = _project_root / ".env"

class BaseAppConfig(BaseSettings):
    """Base configuration class with common settings that can be reused by all config classes."""
    
    model_config = SettingsConfigDict(
        env_file=str(_env_file) if _env_file.exists() else ".env", 
        env_file_encoding="utf-8", 
        case_sensitive=False, 
        extra="ignore"
    )
    
    # Common application settings
    ENV: str = Field(default="development", env="ENV")
    APP_NAME: str = Field(default="DemoManagementService", env="APP_NAME")
    APP_VERSION: str = Field(default="2.0.1", env="APP_VERSION")
    PORT: int = Field(default=8801, env="PORT")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    STATUS: str = Field(default="active", env="STATUS")
    
    # [x]: We also need to add the Dtabase url for Read Replica.
    # Database settings
    POSTGRES_HOST: str = Field(default="localhost", env="POSTGRES_HOST")
    POSTGRES_PORT: int = Field(default=5432, env="POSTGRES_PORT")
    POSTGRES_DB: str = Field(default="demo_management_db", env="POSTGRES_DB")
    POSTGRES_USER: str = Field(default="postgres", env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(default="postgres", env="POSTGRES_PASSWORD")
    ASYNC_DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/demo_management_db",
        env="ASYNC_DATABASE_URL"
    )
    SERVICE_NAME: str = Field(default="demo-management-service", env="SERVICE_NAME")
    
    # Read Replica Database settings
    POSTGRES_READ_HOST: str = Field(default="localhost", env="POSTGRES_READ_HOST")
    POSTGRES_READ_PORT: int = Field(default=5432, env="POSTGRES_READ_PORT")
    POSTGRES_READ_DB: str = Field(default="demo_management_db", env="POSTGRES_READ_DB")
    POSTGRES_READ_USER: str = Field(default="postgres", env="POSTGRES_READ_USER")
    POSTGRES_READ_PASSWORD: str = Field(default="postgres", env="POSTGRES_READ_PASSWORD")
    ASYNC_READ_DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/demo_management_db",
        env="ASYNC_READ_DATABASE_URL"
    )
    

    QUEUE_LOG: bool = Field(default=False, env="QUEUE_LOG")
    
    # CORS settings
    CORS_ORIGINS: str = Field(default="*", env="CORS_ORIGINS")
    
    # Media settings
    MEDIA_PATH: str = Field(default="app/media", env="MEDIA_PATH")
    LOGO_SUBDIR: str = Field(default="logo", env="LOGO_SUBDIR")
    
    # Cache and messaging settings
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    RABBITMQ_URL: str = Field(default="amqp://guest:guest@localhost:5672/", env="RABBITMQ_URL")
    
    # RabbitMQ Queue Names (comma-separated list or individual queue names)
    # Example: "demo_creation_topic,demo_deletion_topic,log_queue"
    RABBITMQ_QUEUE_NAMES: str = Field(
        default="log_queue",
        env="RABBITMQ_QUEUE_NAMES",
        description="Comma-separated list of queue names to ensure exist on startup"
    )
    
    # Service-level enable/disable flags (for individual service opt-in/opt-out)
    # Note: Project always has access, but individual services can choose to use or not use these services
    RABBITMQ_ENABLED: bool = Field(
        default=True,
        env="RABBITMQ_ENABLED",
        description="Enable/disable RabbitMQ usage for this service (service-level opt-in/opt-out)"
    )
    POSTGRES_ENABLED: bool = Field(
        default=True,
        env="POSTGRES_ENABLED",
        description="Enable/disable PostgreSQL usage for this service (service-level opt-in/opt-out)"
    )
    
    # Database routing settings
    USE_READ_REPLICA: bool = Field(default=False, env="USE_READ_REPLICA")
    
    # Wasabi/S3 settings for migration storage
    WASABI_ENDPOINT_URL: str = Field(
        default="https://s3.wasabisys.com",
        env="WASABI_ENDPOINT_URL"
    )
    WASABI_ACCESS_KEY_ID: str = Field(default="", env="WASABI_ACCESS_KEY_ID")
    WASABI_SECRET_ACCESS_KEY: str = Field(default="", env="WASABI_SECRET_ACCESS_KEY")
    WASABI_REGION: str = Field(default="us-east-1", env="WASABI_REGION")
    MIGRATION_BUCKET_NAME: str = Field(default="", env="MIGRATION_BUCKET_NAME")

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return str(self.ENV).lower() in ["production", "prod"]
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return str(self.ENV).lower() in ["development", "dev"]


@lru_cache
def get_base_config() -> BaseAppConfig:
    """Get cached base configuration instance."""
    return BaseAppConfig()
