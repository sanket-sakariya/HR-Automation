from __future__ import annotations
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

from app.config.database import async_engine
from app.config.config import config
from app.config.logger_config import logger
from app.schema.database_schema import (
    DatabaseOperationRequestSchema,
    DatabaseOperationResponseSchema,
    MigrationUploadRequestSchema,
    MigrationDownloadRequestSchema,
    MigrationOperationResponseSchema
)
from app.schema.response_schema import ApiResponseSchema
from app.model.baseapp_model import Base


router = APIRouter()


def get_alembic_config() -> Config:
    """Get Alembic configuration."""
    # Get the project root directory
    # File is at: app/api/v1/endpoints/database_endpoint.py
    # Need to go up 5 levels to reach project root
    project_root = Path(__file__).parent.parent.parent.parent.parent
    alembic_ini_path = project_root / "alembic.ini"
    
    # Verify alembic.ini exists
    if not alembic_ini_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Alembic configuration file not found: {alembic_ini_path}"
        )
    
    # Verify alembic directory exists
    alembic_dir = project_root / "alembic"
    if not alembic_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Alembic directory not found: {alembic_dir}"
        )
    
    # Create Alembic config with absolute path to ini file
    alembic_cfg = Config(str(alembic_ini_path))
    
    # Override database URL from app config
    # Use ASYNC_DATABASE_URL for Alembic (env.py handles async internally)
    database_url = config.ASYNC_DATABASE_URL
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    
    # Ensure script_location is set correctly (relative to project root)
    script_location = alembic_cfg.get_main_option("script_location")
    if not script_location:
        alembic_cfg.set_main_option("script_location", "alembic")
    
    return alembic_cfg


async def get_current_revision() -> Optional[str]:
    """Get the current database revision."""
    try:
        async with async_engine.connect() as connection:
            # Check if alembic_version table exists
            result = await connection.execute(
                text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'alembic_version'
                    )
                """)
            )
            table_exists = result.scalar()
            
            if not table_exists:
                return None
            
            # Get current revision
            result = await connection.execute(
                text("SELECT version_num FROM alembic_version LIMIT 1")
            )
            revision = result.scalar()
            return revision
    except Exception as e:
        logger.error(f"Error getting current revision: {str(e)}")
        return None


@router.post("/database/", response_model=ApiResponseSchema[DatabaseOperationResponseSchema])
async def database_operation(
    request: DatabaseOperationRequestSchema
):
    """
    Perform database operations: initialize, upgrade, or create revision.
    
    Operations:
    - initialize: Create all tables from models (uses Base.metadata.create_all)
    - upgrade: Run Alembic migrations up to specified revision (default: head)
    - revision: Create a new Alembic revision with autogenerate
    """
    try:
        if request.operation == "initialize":
            # Initialize database by creating all tables
            logger.info("Initializing database: Creating all tables from models")
            
            try:
                # Ensure all models are imported and registered with Base.metadata
                # Models are imported at the top of the file
                
                # Create all tables using the async engine
                async with async_engine.begin() as connection:
                    def create_tables(conn):
                        Base.metadata.create_all(bind=conn)
                    
                    await connection.run_sync(create_tables)
                
                # Note: initialize doesn't create alembic_version table
                # That's only created when Alembic migrations run
                # If you want alembic_version table, use upgrade operation instead
                
                current_rev = await get_current_revision()
                
                response_data = DatabaseOperationResponseSchema(
                    operation="initialize",
                    success=True,
                    message="Database initialized successfully. All tables created. Note: alembic_version table is not created. Use 'upgrade' operation to run migrations.",
                    current_revision=current_rev
                )
                
                logger.info("Database initialization completed successfully")
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Database initialization failed: {error_msg}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database initialization failed: {error_msg}"
                ) from e
            
        elif request.operation == "upgrade":
            # Get Alembic config for upgrade operation
            alembic_cfg = get_alembic_config()
            
            # Check if there are any migration files
            project_root = Path(__file__).parent.parent.parent.parent.parent
            versions_dir = project_root / "alembic" / "versions"
            migration_files = list(versions_dir.glob("*.py")) if versions_dir.exists() else []
            
            if not migration_files:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No migration files found. Please create a migration first using the 'revision' operation with a message."
                )
            
            # Upgrade database to specified revision
            target_revision = request.revision or "head"
            logger.info(f"Upgrading database to revision: {target_revision}")
            
            try:
                original_cwd = os.getcwd()
                
                def run_upgrade():
                    """Run Alembic upgrade in a separate thread to avoid event loop conflicts."""
                    try:
                        # Change to project root for Alembic commands
                        # Alembic needs to be in the project root to resolve relative paths
                        os.chdir(str(project_root))
                        
                        # Run upgrade command
                        # This will create alembic_version table if it doesn't exist
                        command.upgrade(alembic_cfg, target_revision)
                    finally:
                        # Restore working directory
                        os.chdir(original_cwd)
                
                # Run in thread pool to avoid asyncio event loop conflicts
                # Alembic's env.py uses asyncio.run() which can't be called from a running event loop
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    await loop.run_in_executor(executor, run_upgrade)
                
                # Wait a bit for the migration to complete and table to be created
                await asyncio.sleep(0.1)
                
                current_rev = await get_current_revision()
                
                response_data = DatabaseOperationResponseSchema(
                    operation="upgrade",
                    success=True,
                    message=f"Database upgraded successfully to revision: {target_revision}",
                    current_revision=current_rev
                )
                
                logger.info(f"Database upgrade completed. Current revision: {current_rev}")
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Upgrade failed: {error_msg}", exc_info=True)
                
                # Provide more specific error messages
                if "script_location" in error_msg.lower():
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Alembic configuration error: {error_msg}. Please ensure alembic.ini and alembic/ directory exist."
                    ) from e
                elif "no such revision" in error_msg.lower():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Revision not found: {error_msg}. Please check available revisions."
                    ) from e
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database upgrade failed: {error_msg}"
                ) from e
            
        elif request.operation == "revision":
            # Get Alembic config for revision operation
            alembic_cfg = get_alembic_config()
            
            # Create a new revision
            if not request.message:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Message is required for revision operation"
                )
            
            logger.info(f"Creating new revision with message: {request.message}")
            
            try:
                project_root = Path(__file__).parent.parent.parent.parent.parent
                original_cwd = os.getcwd()
                
                # Ensure versions directory exists before creating revision
                versions_dir = project_root / "alembic" / "versions"
                versions_dir.mkdir(parents=True, exist_ok=True)
                
    
                def run_revision():
                    """Run Alembic revision in a separate thread to avoid event loop conflicts."""
                    try:
                        # Change to project root for Alembic commands
                        # Alembic needs to be in the project root to resolve relative paths
                        os.chdir(str(project_root))
                        
                        # Run revision command with autogenerate
                        command.revision(
                            alembic_cfg,
                            autogenerate=True,
                            message=request.message
                        )
                    finally:
                        # Restore working directory
                        os.chdir(original_cwd)
                
                # Run in thread pool to avoid asyncio event loop conflicts
                # Alembic's env.py uses asyncio.run() which can't be called from a running event loop
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    await loop.run_in_executor(executor, run_revision)
                
                # Get the latest revision ID from the versions directory
                script = ScriptDirectory.from_config(alembic_cfg)
                head_revision = script.get_current_head()
                
                # Upload new migrations to Wasabi after successful creation
                versions_dir = project_root / "alembic" / "versions"
                if head_revision and versions_dir.exists():
                    try:
                        from app.helper.migration_storage import MigrationStorageService
                        storage_service = MigrationStorageService()
                        
                        # Upload to Wasabi with revision ID as version
                        upload_success = storage_service.upload_migrations(
                            versions_dir,
                            version=head_revision
                        )
                        if upload_success:
                            logger.info(
                                f"Successfully uploaded migration {head_revision} to Wasabi"
                            )
                        else:
                            logger.warning(
                                f"Failed to upload migration {head_revision} to Wasabi. "
                                "Please upload manually."
                            )
                    except Exception as upload_error:
                        # Don't fail the revision creation if upload fails
                        logger.error(
                            f"Error uploading migration to Wasabi: {str(upload_error)}",
                            exc_info=True
                        )
                
                current_rev = await get_current_revision()
                
                response_data = DatabaseOperationResponseSchema(
                    operation="revision",
                    success=True,
                    message=f"Revision created successfully with message: '{request.message}'",
                    revision_id=head_revision,
                    current_revision=current_rev
                )
                
                logger.info(f"Revision created: {head_revision}")
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Revision creation failed: {error_msg}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Revision creation failed: {error_msg}"
                ) from e
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown operation: {request.operation}"
            )
        
        return ApiResponseSchema[DatabaseOperationResponseSchema](
            success=True,
            data=response_data,
            message="Database operation completed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database operation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database operation failed: {str(e)}"
        ) from e


@router.post("/database/upload", response_model=ApiResponseSchema[MigrationOperationResponseSchema])
async def upload_migrations(request: MigrationUploadRequestSchema):
    """Upload migration files to Wasabi/S3."""
    try:
        project_root = Path(__file__).parent.parent.parent.parent.parent
        migrations_path = project_root / "alembic" / "versions"
        
        if not migrations_path.exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Migrations directory not found: {migrations_path}"
            )
        
        migration_files = list(migrations_path.glob("*.py"))
        if not migration_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No migration files found in {migrations_path}"
            )
        
        from app.helper.migration_storage import MigrationStorageService
        storage_service = MigrationStorageService()
        
        if not storage_service._is_configured():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Wasabi/S3 not configured. Set WASABI_ACCESS_KEY_ID, WASABI_SECRET_ACCESS_KEY, and MIGRATION_BUCKET_NAME"
            )
        
        logger.info(f"Uploading {len(migration_files)} migration file(s) to Wasabi...")
        
        # Run upload in thread pool to avoid blocking (always use latest)
        def run_upload():
            return storage_service.upload_migrations(migrations_path, version=None)
        
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            success = await loop.run_in_executor(executor, run_upload)
        
        if success:
            zip_filename = f"{config.SERVICE_NAME}-migrations.zip"
            location = f"migrations/latest/{zip_filename}"
            
            response_data = MigrationOperationResponseSchema(
                operation="upload",
                success=True,
                message=f"Successfully uploaded {len(migration_files)} migration file(s) to Wasabi",
                file_count=len(migration_files),
                location=location
            )
            
            logger.info(f"Migration upload completed: {location}")
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload migrations to Wasabi"
            )
        
        return ApiResponseSchema[MigrationOperationResponseSchema](
            success=True,
            data=response_data,
            message="Migration upload completed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Migration upload failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration upload failed: {str(e)}"
        ) from e


@router.post("/database/download", response_model=ApiResponseSchema[MigrationOperationResponseSchema])
async def download_migrations(request: MigrationDownloadRequestSchema):
    """Download migration files from Wasabi/S3."""
    try:
        project_root = Path(__file__).parent.parent.parent.parent.parent
        migrations_path = project_root / "alembic" / "versions"
        
        from app.helper.migration_storage import MigrationStorageService
        storage_service = MigrationStorageService()
        
        if not storage_service._is_configured():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Wasabi/S3 not configured. Set WASABI_ACCESS_KEY_ID, WASABI_SECRET_ACCESS_KEY, and MIGRATION_BUCKET_NAME"
            )
        
        logger.info("Downloading migrations from Wasabi...")
        
        # Run download in thread pool to avoid blocking (always use latest)
        def run_download():
            return storage_service.download_migrations(migrations_path, version=None)
        
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            success = await loop.run_in_executor(executor, run_download)
        
        if success:
            migration_files = list(migrations_path.glob("*.py")) if migrations_path.exists() else []
            
            response_data = MigrationOperationResponseSchema(
                operation="download",
                success=True,
                message=f"Successfully downloaded {len(migration_files)} migration file(s) from Wasabi",
                file_count=len(migration_files),
                location=str(migrations_path)
            )
            
            logger.info(f"Migration download completed: {len(migration_files)} files in {migrations_path}")
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to download migrations from Wasabi"
            )
        
        return ApiResponseSchema[MigrationOperationResponseSchema](
            success=True,
            data=response_data,
            message="Migration download completed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Migration download failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration download failed: {str(e)}"
        ) from e