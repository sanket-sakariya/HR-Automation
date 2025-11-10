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

from app.config.database import async_engine
from app.config.config import config
from app.config.logger_config import logger
from app.repository.migration_repository import MigrationRepository
from app.schema.migration_schema import (
    DatabaseOperationResponseSchema,
    MigrationUploadRequestSchema,
    MigrationDownloadRequestSchema,
    MigrationOperationResponseSchema,
    RevisionRequestSchema
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




@router.post("/migration/revision", response_model=ApiResponseSchema[DatabaseOperationResponseSchema])
async def create_revision(request: RevisionRequestSchema):
    """
    Create a new Alembic revision with autogenerate.
    
    Requires a message in the request body: {"message": "your migration message"}
    """
    try:
        # Initialize migration repository
        migration_repo = MigrationRepository()
        
        # Get Alembic config for revision operation
        alembic_cfg = get_alembic_config()
        
        project_root = Path(__file__).parent.parent.parent.parent.parent
        versions_dir = project_root / "alembic" / "versions"
        
        # Validate migration files exist and check for potential mismatches
        migration_files = list(versions_dir.glob("*.py")) if versions_dir.exists() else []
        current_db_rev = await migration_repo.get_current_revision()
        
        # Check if there's a mismatch between database and migration files
        if current_db_rev:
            try:
                script = ScriptDirectory.from_config(alembic_cfg)
                # Try to get the revision from script directory
                try:
                    script.get_revision(current_db_rev)
                except Exception:
                    # Database revision not found in migration files
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Database revision '{current_db_rev}' not found in local migration files. "
                            f"This usually means migration files are out of sync. "
                            f"Please download migrations using '/migration/download' endpoint or "
                            f"ensure all migration files are present in {versions_dir}. "
                            f"Current migration files: {len(migration_files)}"
                        )
                    )
            except HTTPException:
                raise
            except Exception as e:
                # If we can't validate, log but continue (might be first migration)
                logger.warning(f"Could not validate database revision: {str(e)}")
        
        logger.info(f"Creating new revision with message: {request.message}")
        
        try:
            original_cwd = os.getcwd()
            
            # Ensure versions directory exists before creating revision
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
            
            current_rev = await migration_repo.get_current_revision()
            
            response_data = DatabaseOperationResponseSchema(
                operation="revision",
                success=True,
                message=f"Revision created successfully with message: '{request.message}'",
                revision_id=head_revision,
                current_revision=current_rev
            )
            
            logger.info(f"Revision created: {head_revision}")
        except HTTPException:
            raise
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Revision creation failed: {error_msg}", exc_info=True)
            
            # Provide more helpful error messages for common issues
            if "can't locate revision" in error_msg.lower() or "can't find revision" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Revision mismatch error: {error_msg}. "
                        f"This usually means the database references a revision that doesn't exist in local migration files. "
                        f"Please download migrations using '/migration/download' endpoint or "
                        f"check that all migration files are present in {versions_dir}."
                    )
                ) from e
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Revision creation failed: {error_msg}"
            ) from e
        
        return ApiResponseSchema[DatabaseOperationResponseSchema](
            success=True,
            data=response_data,
            message="Revision created successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Revision creation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Revision creation failed: {str(e)}"
        ) from e


@router.post("/migration/upgrade", response_model=ApiResponseSchema[DatabaseOperationResponseSchema])
async def upgrade_database():
    """
    Upgrade database to the latest revision (head).
    
    Automatically upgrades to the latest migration without requiring any request body.
    """
    try:
        # Initialize migration repository
        migration_repo = MigrationRepository()
        
        # Get Alembic config for upgrade operation
        alembic_cfg = get_alembic_config()
        
        # Check if there are any migration files
        project_root = Path(__file__).parent.parent.parent.parent.parent
        versions_dir = project_root / "alembic" / "versions"
        migration_files = list(versions_dir.glob("*.py")) if versions_dir.exists() else []
        
        if not migration_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No migration files found. Please create a migration first using the '/migration/revision' endpoint with a message."
            )
        
        # Upgrade database to head
        target_revision = "head"
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
            
            current_rev = await migration_repo.get_current_revision()
            
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
        
        return ApiResponseSchema[DatabaseOperationResponseSchema](
            success=True,
            data=response_data,
            message="Database upgrade completed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database upgrade failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database upgrade failed: {str(e)}"
        ) from e


@router.post("/migration/upload", response_model=ApiResponseSchema[MigrationOperationResponseSchema])
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


@router.post("/migration/download", response_model=ApiResponseSchema[MigrationOperationResponseSchema])
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