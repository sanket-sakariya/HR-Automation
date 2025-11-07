"""Download migration files from Wasabi/S3.

Usage:
    python scripts/download_migrations.py
    python scripts/download_migrations.py --version v1.0.0
    python scripts/download_migrations.py --output-dir ./local_migrations
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
    """Download migrations from Wasabi."""
    parser = argparse.ArgumentParser(description="Download migration files from Wasabi/S3")
    parser.add_argument("--version", type=str, default=None, help="Version tag (default: latest)")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory path")
    args = parser.parse_args()
    
    # Setup paths
    output_path = Path(args.output_dir) if args.output_dir else project_root / "alembic" / "versions"
    
    # Initialize and download
    storage_service = MigrationStorageService()
    
    if not storage_service._is_configured():
        logger.error("❌ Wasabi/S3 not configured. Set WASABI_ACCESS_KEY_ID, WASABI_SECRET_ACCESS_KEY, and MIGRATION_BUCKET_NAME")
        sys.exit(1)
    
    version = args.version or "latest"
    logger.info(f"Downloading migrations from Wasabi (version: {version})...")
    
    if storage_service.download_migrations(output_path, version=version):
        migration_files = list(output_path.glob("*.py"))
        logger.info(f"✅ Successfully downloaded {len(migration_files)} migration file(s) to {output_path}")
        sys.exit(0)
    else:
        logger.error("❌ Failed to download migrations from Wasabi")
        sys.exit(1)


if __name__ == "__main__":
    main()

