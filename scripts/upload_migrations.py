"""Upload migration files to Wasabi/S3.

Usage:
    python scripts/upload_migrations.py
    python scripts/upload_migrations.py --version v1.0.0
"""
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Setup
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env file
load_dotenv(dotenv_path=project_root / ".env", override=True)

# Clear config cache and import
from app.config.config import get_config
get_config.cache_clear()

from app.helper.migration_storage import MigrationStorageService
from app.config.logger_config import logger


def main():
    """Upload migrations to Wasabi."""
    parser = argparse.ArgumentParser(description="Upload migration files to Wasabi/S3")
    parser.add_argument("--version", type=str, default=None, help="Version tag (default: latest)")
    parser.add_argument("--migrations-dir", type=str, default=None, help="Migrations directory path")
    args = parser.parse_args()
    
    # Setup paths
    migrations_path = Path(args.migrations_dir) if args.migrations_dir else project_root / "alembic" / "versions"
    
    if not migrations_path.exists():
        logger.error(f"Migrations directory not found: {migrations_path}")
        sys.exit(1)
    
    migration_files = list(migrations_path.glob("*.py"))
    if not migration_files:
        logger.warning(f"No migration files found in {migrations_path}")
        sys.exit(1)
    
    # Initialize and upload
    storage_service = MigrationStorageService()
    
    if not storage_service._is_configured():
        logger.error("❌ Wasabi/S3 not configured. Set WASABI_ACCESS_KEY_ID, WASABI_SECRET_ACCESS_KEY, and MIGRATION_BUCKET_NAME")
        sys.exit(1)
    
    version = args.version or "latest"
    logger.info(f"Uploading {len(migration_files)} migration file(s) to Wasabi (version: {version})...")
    
    if storage_service.upload_migrations(migrations_path, version=version):
        from app.config.config import config
        zip_filename = f"{config.SERVICE_NAME}-migrations.zip"
        logger.info(f"✅ Successfully uploaded migrations to Wasabi!")
        logger.info(f"   Location: migrations/{version}/{zip_filename}")
        sys.exit(0)
    else:
        logger.error("❌ Failed to upload migrations to Wasabi")
        sys.exit(1)


if __name__ == "__main__":
    main()

