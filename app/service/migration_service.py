from __future__ import annotations

from pathlib import Path
from fastapi import HTTPException, status
from alembic.config import Config

from app.config.config import config
from app.helper.path_helper import PathHelper

def get_alembic_config() -> Config:
    """Get Alembic configuration."""
    try:
        # Find project root dynamically
        project_root = PathHelper.find_project_root(Path(__file__))
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Project root not found: {e}"
        ) from e

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