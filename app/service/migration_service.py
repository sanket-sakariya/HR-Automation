from __future__ import annotations

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.config.baseapp_config import get_base_config
from app.config.logger_config import logger
from app.helper.migration_helper import MigrationHelper
from app.helper.path_helper import PathHelper
from app.repository.migration_repository import MigrationRepository
from app.schema.migration_schema import MigrationResponseSchema
from app.service.baseapp_service import BaseAppService


class MigrationService(BaseAppService):
    """Service for handling database migrations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db)
        self.base_config = get_base_config()
        self.alembic_cfg = self._get_alembic_config()
        self.migration_repo = MigrationRepository(db)
        self.migration_helper = MigrationHelper()

    def _get_alembic_config(self) -> Config:
        """Get Alembic configuration."""
        try:
            project_root = PathHelper.find_project_root(Path(__file__))
        except FileNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Project root not found: {e}",
            ) from e

        alembic_ini_path = project_root / "alembic.ini"
        if not alembic_ini_path.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Alembic configuration file not found: {alembic_ini_path}",
            )

        alembic_dir = project_root / "alembic"
        if not alembic_dir.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Alembic directory not found: {alembic_dir}",
            )

        alembic_cfg = Config(str(alembic_ini_path))
        database_url = get_base_config().ASYNC_DATABASE_URL
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)
        script_location = alembic_cfg.get_main_option("script_location")
        if not script_location:
            alembic_cfg.set_main_option("script_location", "alembic")

        return alembic_cfg

    async def _run_alembic_command(self, command_name: str, **kwargs):
        """Run an Alembic command in a separate thread to avoid event loop conflicts."""
        original_cwd = os.getcwd()
        project_root = PathHelper.find_project_root(Path(__file__))

        def run_command_in_thread():
            try:
                os.chdir(str(project_root))
                alembic_func = getattr(command, command_name)
                alembic_func(self.alembic_cfg, **kwargs)
            finally:
                os.chdir(original_cwd)

        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            return await loop.run_in_executor(executor, run_command_in_thread)

    async def create_revision(self, message: str) -> MigrationResponseSchema:
        """Create a new Alembic revision."""
        if not self.base_config.POSTGRES_ENABLED:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="PostgreSQL is disabled. Set POSTGRES_ENABLED=True.",
            )

        current_db_rev = await self.migration_repo.get_current_revision()
        if current_db_rev:
            script = ScriptDirectory.from_config(self.alembic_cfg)
            try:
                script.get_revision(current_db_rev)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"DB rev '{current_db_rev}' not in local files.",
                ) from e

        logger.info(f"Creating new revision with message: {message}")
        await self._run_alembic_command(
            "revision", autogenerate=True, message=message
        )

        script = ScriptDirectory.from_config(self.alembic_cfg)
        head_revision = script.get_current_head()
        current_rev = await self.migration_repo.get_current_revision()

        return MigrationResponseSchema(
            operation="revision",
            success=True,
            message=f"Revision created successfully with message: '{message}'",
            revision_id=head_revision,
            current_revision=current_rev,
        )

    async def upgrade_database(self) -> MigrationResponseSchema:
        """Upgrade database to the latest revision."""
        if not self.base_config.POSTGRES_ENABLED:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="PostgreSQL is disabled. Set POSTGRES_ENABLED=True.",
            )

        project_root = PathHelper.find_project_root(Path(__file__))
        versions_dir = project_root / "alembic" / "versions"
        if not any(versions_dir.glob("*.py")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No migration files found. Please create a migration first.",
            )

        logger.info("Upgrading database to revision: head")
        await self._run_alembic_command("upgrade", revision="head")
        await asyncio.sleep(0.1)
        current_rev = await self.migration_repo.get_current_revision()
        return MigrationResponseSchema(
            operation="upgrade",
            success=True,
            message="Database upgraded successfully",
            current_revision=current_rev,
        )

    async def upload_migrations(self) -> MigrationResponseSchema:
        """Upload migration files to Wasabi/S3."""
        if not self.migration_helper._is_configured(): 
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Wasabi/S3 not configured.",
            )

        project_root = PathHelper.find_project_root(Path(__file__))
        migrations_path = project_root / "alembic" / "versions"
        if not migrations_path.exists() or not any(migrations_path.glob("*.py")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No migration files found in {migrations_path}",
            )

        logger.info("Uploading migration files to Wasabi...")
        success = await asyncio.get_event_loop().run_in_executor(
            None, self.migration_helper.upload_migrations, migrations_path, None
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload migrations to Wasabi",
            )

        zip_filename = f"{self.base_config.SERVICE_NAME}-migrations.zip"
        return MigrationResponseSchema(
            operation="upload",
            success=True,
            message="Migration files uploaded successfully",
            file_count=len(list(migrations_path.glob("*.py"))),
            location=f"migrations/latest/{zip_filename}",
        )

    async def download_migrations(self) -> MigrationResponseSchema:
        """Download migration files from Wasabi/S3."""
        if not self.migration_helper._is_configured():  
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Wasabi/S3 not configured.",
            )

        migrations_path = PathHelper.find_project_root(Path(__file__)) / "alembic" / "versions"
        logger.info("Downloading migrations from Wasabi...")
        success = await asyncio.get_event_loop().run_in_executor(
            None, self.migration_helper.download_migrations, migrations_path, None
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to download migrations from Wasabi",
            )

        return MigrationResponseSchema(
            operation="download",
            success=True,
            message="Migration files downloaded successfully",
            file_count=len(list(migrations_path.glob("*.py"))),
            location=str(migrations_path),
        )