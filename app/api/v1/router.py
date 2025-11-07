from fastapi import APIRouter

from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.demo_endpoint import router as demo_router
from app.api.v1.endpoints.database_endpoint import router as database_router


api_router: APIRouter = APIRouter()

api_router.include_router(router=health_router,  tags=["Health"])  # /health/
api_router.include_router(router=demo_router,  tags=["Demo"])  # /demo/
api_router.include_router(router=database_router,  tags=["Database"])  # /database/
