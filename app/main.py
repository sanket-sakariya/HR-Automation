from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.config.baseapp_config import get_base_config
from app.config.config import config
from app.config.logger_config import (
    _GLOBAL_QUEUE_HANDLER,
    configure_logging,
    logger,
    shutdown_logging,
)
from app.exception.fastapi.error_handlers import setup_error_handlers
from app.helper.migration_helper import MigrationHelper
from app.middleware.correlation import CorrelationIdMiddleware


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Handles application startup and shutdown events.
    """
    base_config = get_base_config()
    
    # Startup
    configure_logging()
    
    # Initialize queue log handler if enabled

    if _GLOBAL_QUEUE_HANDLER:
        await _GLOBAL_QUEUE_HANDLER.initialize()
    
    # Log service status
    if base_config.POSTGRES_ENABLED:
        logger.info("✅ PostgreSQL is enabled for this service")
    else:
        logger.warning("⚠️  PostgreSQL is disabled for this service (POSTGRES_ENABLED=False)")
    
    if base_config.RABBITMQ_ENABLED:
        logger.info("✅ RabbitMQ is enabled for this service")
    else:
        logger.warning("⚠️  RabbitMQ is disabled for this service (RABBITMQ_ENABLED=False)")
    
    # Ensure migration files exist (download from Wasabi if needed)
    # This is critical because migration files are excluded from Docker image via .dockerignore
    # Only check migrations if PostgreSQL is enabled for this service
    if base_config.POSTGRES_ENABLED:

        
        project_root = Path(__file__).parent.parent.parent
        migrations_path = project_root / "alembic" / "versions"
        
        migration_helper = MigrationHelper()
        migrations_exist = migration_helper.ensure_migrations_exist(migrations_path)
        
        if not migrations_exist:
            logger.warning(
                "⚠️  Migration files not found and could not be downloaded from Wasabi. "
                "Database migrations may fail. Please ensure migrations are uploaded to Wasabi."
            )
        else:
            logger.info("✅ Migration files are ready")
    
    yield
    # Shutdown
    await shutdown_logging()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    fastapi_app = FastAPI(
        title=config.APP_NAME,
        version=config.APP_VERSION,
        docs_url=None,
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        default_response_class=JSONResponse,
        lifespan=lifespan,
    )

    # Add middleware
    fastapi_app.add_middleware(CorrelationIdMiddleware, header_name="X-Correlation-ID")
    
    # Setup custom error handlers
    setup_error_handlers(fastapi_app)

    # Include API routes
    fastapi_app.include_router(router=api_router, prefix=f"/{config.SERVICE_NAME}/api/v1")
    
    # Mount static files for media
    fastapi_app.mount("/media", StaticFiles(directory="app/media"), name="media")
    
    # Custom Swagger UI with sidebar
    @fastapi_app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        template_path = Path(__file__).parent / "templates" / "swagger-ui-theme.html"
        html_content = template_path.read_text(encoding="utf-8")
        return HTMLResponse(content=html_content)

    return fastapi_app

if __name__ == "__main__":
    import uvicorn
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8801)