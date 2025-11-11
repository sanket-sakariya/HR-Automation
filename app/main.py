from pathlib import Path
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.config.config import config
from app.config.logger_config import configure_logging, shutdown_logging, logger
from app.api.v1.router import api_router
from app.middleware.correlation import CorrelationIdMiddleware
from app.exception.fastapi.error_handlers import setup_error_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):  # pylint: disable=unused-argument
    """Manage application lifespan events."""
    # Startup
    configure_logging()
    
    # Initialize queue log handler if enabled
    from app.config.logger_config import _GLOBAL_QUEUE_HANDLER
    if _GLOBAL_QUEUE_HANDLER:
        await _GLOBAL_QUEUE_HANDLER._initialize()
    
    # Ensure migration files exist (download from Wasabi if needed)
    # This is critical because migration files are excluded from Docker image via .dockerignore
    from app.helper.migration_helper import MigrationHelper
    from pathlib import Path
    
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
    app = FastAPI(
        title=config.APP_NAME,
        version=config.APP_VERSION,
        docs_url=None,
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        default_response_class=JSONResponse,
        lifespan=lifespan,
    )

    # Add middleware
    app.add_middleware(CorrelationIdMiddleware, header_name="X-Correlation-ID")
    
    # Setup custom error handlers
    setup_error_handlers(app)

    # Include API routes
    app.include_router(router=api_router, prefix="/demo-management-service/api/v1")
    
    # Mount static files for media
    app.mount("/media", StaticFiles(directory="app/media"), name="media")
    
    # Custom Swagger UI with sidebar
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        template_path = Path(__file__).parent / "templates" / "swagger-ui-theme.html"
        html_content = template_path.read_text(encoding="utf-8")
        return HTMLResponse(content=html_content)

    return app