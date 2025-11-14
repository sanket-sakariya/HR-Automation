"""APISIX Gateway Configuration."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class APISIXConfig(BaseSettings):
    """Configuration for APISIX Gateway integration."""
    
    # APISIX Configuration
    APISIX_ADMIN_URL: str = "http://localhost:9180"
    APISIX_ADMIN_API_KEY: str = ""
    APISIX_JWT_SECRET: str = ""
    APISIX_ROUTE_NAME: str = "demo-management-route"
    IS_APISIX_ENABLED: bool = False
    
    # Service Configuration (from base config)
    SERVICE_NAME: str = "demo-management-service"
    APP_PORT: int = 8801
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


# Global instance
_apisix_config: APISIXConfig | None = None


def get_apisix_config() -> APISIXConfig:
    """Get the APISIX configuration instance."""
    global _apisix_config
    if _apisix_config is None:
        _apisix_config = APISIXConfig()
    return _apisix_config
