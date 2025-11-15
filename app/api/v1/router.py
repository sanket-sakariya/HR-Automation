"""API router for version 1."""
from fastapi import APIRouter

from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.migration_endpoint import router as migration_router
from app.api.v1.endpoints.demo_endpoint import router as demo_router
from app.api.v1.endpoints.backup_endpoint import router as backup_router
from app.config.baseapp_config import get_base_config


api_router = APIRouter()

api_router.include_router(health_router, tags=["health"])
api_router.include_router(migration_router, tags=["migrations"])
api_router.include_router(demo_router, tags=["demos"])
api_router.include_router(backup_router, tags=["backup"])

# Conditionally include RabbitMQ router only if enabled
base_config = get_base_config()
if base_config.IS_RABBITMQ_ENABLED:
    from app.api.v1.endpoints.rabbitmq_endpoint import router as rabbitmq_router
    api_router.include_router(rabbitmq_router, tags=["rabbitmq"])
