from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.helper.redis_helper import get_redis_helper
from app.helper.apisix_helper import get_apisix_helper
from app.helper.rabbitmq_helper import RabbitMQHelper
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
async def lifespan(app: FastAPI):
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
    if base_config.IS_POSTGRES_ENABLED:
        logger.info("✅ PostgreSQL is enabled for this service")
    else:
        logger.warning(
            "⚠️  PostgreSQL is disabled for this service (IS_POSTGRES_ENABLED=False)"
        )

    if base_config.IS_RABBITMQ_ENABLED:
        logger.info("✅ RabbitMQ is enabled for this service")
        # Initialize queues from config
        try:
            rabbitmq_helper = RabbitMQHelper()
            initialized_queues = await rabbitmq_helper.initialize_queues_from_config()
            logger.info(f"✅ Initialized {len(initialized_queues)} RabbitMQ queues")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"⚠️  RabbitMQ queue initialization failed: {e}")
    else:
        logger.warning(
            "⚠️  RabbitMQ is disabled for this service (IS_RABBITMQ_ENABLED=False)"
        )

    # Initialize Redis cache if enabled
    if base_config.IS_REDIS_CACHE_ENABLED:
        try:
            redis_helper = get_redis_helper()
            await redis_helper.initialize()
            logger.info("✅ Redis cache is enabled for this service")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"⚠️  Redis cache initialization failed: {e}")
    else:
        logger.warning(
            "⚠️  Redis cache is disabled for this service (IS_REDIS_CACHE_ENABLED=False)"
        )

    # Ensure migration files exist (download from Wasabi if needed)
    # This is critical because migration files are excluded from Docker image via .dockerignore
    # Only check migrations if PostgreSQL is enabled for this service
    if base_config.IS_POSTGRES_ENABLED:
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

    # Register service with APISIX Gateway
    apisix_helper = get_apisix_helper()
    
    # Check if individual route registration is enabled
    use_individual_routes = getattr(base_config, 'USE_INDIVIDUAL_APISIX_ROUTES', False)
    
    if use_individual_routes:
        # Register each route individually for granular control
        logger.info("🔧 Using individual APISIX route registration mode")
        await apisix_helper.register_individual_routes(app)
    else:
        # Traditional wildcard registration (/{service_name}/*)
        logger.info("🔧 Using wildcard APISIX route registration mode")
        await apisix_helper.register_route()

    yield
    # Shutdown
    redis_helper = get_redis_helper()
    await redis_helper.close()
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
    fastapi_app.include_router(
        router=api_router, prefix=f"/{config.SERVICE_NAME}/api/v1"
    )

    # Mount static files for media
    fastapi_app.mount("/media", StaticFiles(directory="app/media"), name="media")

    # Custom Swagger UI with sidebar
    @fastapi_app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        template_path = Path(__file__).parent / "templates" / "swagger-ui-theme.html"
        html_content = template_path.read_text(encoding="utf-8")
        # Inject the openapi_url dynamically
        html_content = html_content.replace("{{openapi_url}}", fastapi_app.openapi_url)
        return HTMLResponse(content=html_content)

    return fastapi_app


if __name__ == "__main__":
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=get_base_config.APP_PORT)
