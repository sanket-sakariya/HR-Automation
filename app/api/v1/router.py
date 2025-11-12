"""API router for version 1."""
from fastapi import APIRouter

from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.migration_endpoint import router as migration_router
from app.api.v1.endpoints.demo_endpoint import router as demo_router


api_router = APIRouter()

api_router.include_router(health_router, tags=["health"])
api_router.include_router(migration_router, tags=["migrations"])
api_router.include_router(demo_router, tags=["demos"])
