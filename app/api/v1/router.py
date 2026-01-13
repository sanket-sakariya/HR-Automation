"""API router for version 1."""

from fastapi import APIRouter

from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.migration_endpoint import router as migration_router
from app.config.baseapp_config import get_base_config


api_router = APIRouter()

# Always include health and migration endpoints
api_router.include_router(router=health_router, tags=["health"])
api_router.include_router(router=migration_router, tags=["migrations"])

# Get configuration
base_config = get_base_config()

# Conditionally include demo endpoints only if enabled
if base_config.IS_DEMO_ENDPOINTS_ENABLED:
    from app.api.v1.endpoints.demo_a_endpoint import router as demo_a_router
    from app.api.v1.endpoints.demo_b_endpoint import router as demo_b_router
    from app.api.v1.endpoints.demo_a_to_demo_b_mapping_endpoint import (
        router as demo_a_to_demo_b_mapping_router,
    )
    from app.api.v1.endpoints.demo_a_response_endpoint import (
        router as demo_a_response_router,
    )
    from app.api.v1.endpoints.demo_b_response_endpoint import (
        router as demo_b_response_router,
    )

    api_router.include_router(router=demo_a_router, tags=["demo-a"])
    api_router.include_router(router=demo_b_router, tags=["demo-b"])
    api_router.include_router(
        router=demo_a_to_demo_b_mapping_router, tags=["demo-a-to-demo-b-mapping"]
    )
    api_router.include_router(router=demo_a_response_router, tags=["demo-a-response"])
    api_router.include_router(router=demo_b_response_router, tags=["demo-b-response"])

# Conditionally include backup endpoint only if enabled
if base_config.IS_BACKUP_ENABLED:
    from app.api.v1.endpoints.backup_endpoint import router as backup_router

    api_router.include_router(router=backup_router, tags=["backup"])

# Conditionally include RabbitMQ router only if enabled
if base_config.IS_RABBITMQ_ENABLED:
    from app.api.v1.endpoints.rabbitmq_endpoint import router as rabbitmq_router

    api_router.include_router(router=rabbitmq_router, tags=["rabbitmq"])

# Include company management endpoints
from app.api.v1.endpoints.company_management_endpoint import router as company_management_router
from app.api.v1.endpoints.job_requirement_endpoint import router as job_requirement_router
from app.api.v1.endpoints.candidate_management_endpoint import router as candidate_management_router, test_router
from app.api.v1.endpoints.aptitude_endpoint import router as aptitude_router
api_router.include_router(router=company_management_router, tags=["Company Management"])
api_router.include_router(router=job_requirement_router, tags=["Job Requirements"])
api_router.include_router(router=candidate_management_router, tags=["Candidate Management"])
api_router.include_router(router=test_router, tags=["Aptitude Tests - Generation"])
api_router.include_router(router=aptitude_router, tags=["Aptitude Tests - Management"])