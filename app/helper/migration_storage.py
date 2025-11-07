"""Migration storage service for Wasabi/S3."""
from __future__ import annotations
import os
import zipfile
from pathlib import Path
from typing import Optional
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from app.config.config import config
from app.config.logger_config import logger


class MigrationStorageService:
    """Service to sync migration files with Wasabi/S3 storage."""
    
    def __init__(self):
        """Initialize the migration storage service."""
        self.s3_client = None
        self.bucket_name = config.MIGRATION_BUCKET_NAME
        self.endpoint_url = config.WASABI_ENDPOINT_URL
        self.aws_access_key_id = config.WASABI_ACCESS_KEY_ID
        self.aws_secret_access_key = config.WASABI_SECRET_ACCESS_KEY
        self.region = config.WASABI_REGION
        self.service_name = config.SERVICE_NAME
        
        # Generate migration zip filename with service name
        self.migration_zip_name = f"{self.service_name}-migrations.zip"
        
        # Initialize S3 client if credentials are provided
        if self._is_configured():
            try:
                self.s3_client = boto3.client(
                    's3',
                    endpoint_url=self.endpoint_url,
                    aws_access_key_id=self.aws_access_key_id,
                    aws_secret_access_key=self.aws_secret_access_key,
                    region_name=self.region
                )
                logger.info("Migration storage service initialized with Wasabi/S3")
            except Exception as e:
                logger.warning(f"Failed to initialize S3 client: {str(e)}")
        else:
            logger.warning(
                "Migration storage service not configured. "
                "Set WASABI_ACCESS_KEY_ID, WASABI_SECRET_ACCESS_KEY, and MIGRATION_BUCKET_NAME "
                "to enable migration syncing."
            )
    
    def _is_configured(self) -> bool:
        """Check if Wasabi/S3 is properly configured."""
        return bool(
            self.bucket_name
            and self.aws_access_key_id
            and self.aws_secret_access_key
        )
    
    def download_migrations(
        self,
        local_path: Path,
        version: Optional[str] = None
    ) -> bool:
        """
        Download migration files from Wasabi to local path.
        
        Args:
            local_path: Local directory path to store migrations
            version: Optional version tag to download specific version.
                    If None, downloads 'latest'
        
        Returns:
            True if download was successful, False otherwise
        """
        if not self.s3_client:
            logger.warning("S3 client not configured, skipping migration download")
            return False
        
        try:
            # Determine S3 key based on version (includes service name in filename)
            if version:
                key = f"migrations/{version}/{self.migration_zip_name}"
            else:
                key = f"migrations/latest/{self.migration_zip_name}"
            
            # Create local directory
            local_path.mkdir(parents=True, exist_ok=True)
            zip_path = local_path.parent / self.migration_zip_name
            
            logger.info(f"Downloading migrations from Wasabi: {self.bucket_name}/{key}")
            
            # Download zip file
            self.s3_client.download_file(self.bucket_name, key, str(zip_path))
            
            # Extract zip file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(local_path)
            
            # Clean up zip file
            zip_path.unlink()
            
            # Count extracted files
            migration_files = list(local_path.glob("*.py"))
            logger.info(
                f"Successfully downloaded {len(migration_files)} migration files "
                f"from Wasabi to {local_path}"
            )
            return True
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'NoSuchKey':
                logger.warning(
                    f"Migration file not found in Wasabi: {key}. "
                    "This might be the first deployment."
                )
            else:
                logger.error(f"Failed to download migrations from Wasabi: {str(e)}")
            return False
        except NoCredentialsError:
            logger.error("Wasabi credentials not found or invalid")
            return False
        except Exception as e:
            logger.error(f"Error downloading migrations: {str(e)}", exc_info=True)
            return False
    
    def upload_migrations(
        self,
        local_path: Path,
        version: Optional[str] = None
    ) -> bool:
        """
        Upload migration files to Wasabi.
        
        Args:
            local_path: Local directory path containing migration files
            version: Optional version tag. If None, uses 'latest'
        
        Returns:
            True if upload was successful, False otherwise
        """
        if not self.s3_client:
            logger.warning("S3 client not configured, skipping migration upload")
            return False
        
        if not local_path.exists():
            logger.error(f"Migration directory does not exist: {local_path}")
            return False
        
        # Get all migration files
        migration_files = list(local_path.glob("*.py"))
        if not migration_files:
            logger.warning(f"No migration files found in {local_path}")
            return False
        
        try:
            # Create zip file in parent directory (with service name)
            zip_path = local_path.parent / self.migration_zip_name
            
            logger.info(f"Creating migration archive '{self.migration_zip_name}' with {len(migration_files)} files...")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in migration_files:
                    # Preserve directory structure relative to local_path
                    arcname = file_path.name  # Just the filename, not the full path
                    zipf.write(file_path, arcname)
            
            # Upload to both latest and versioned locations if version provided
            # File names include service name
            keys_to_upload = [f"migrations/latest/{self.migration_zip_name}"]
            if version:
                keys_to_upload.append(f"migrations/{version}/{self.migration_zip_name}")
            
            for key in keys_to_upload:
                logger.info(f"Uploading migrations to Wasabi: {self.bucket_name}/{key}")
                self.s3_client.upload_file(str(zip_path), self.bucket_name, key)
            
            # Clean up zip file
            zip_path.unlink()
            
            logger.info(
                f"Successfully uploaded {len(migration_files)} migration files to Wasabi "
                f"(version: {version or 'latest'})"
            )
            return True
            
        except NoCredentialsError:
            logger.error("Wasabi credentials not found or invalid")
            return False
        except Exception as e:
            logger.error(f"Error uploading migrations: {str(e)}", exc_info=True)
            # Clean up zip file if it exists (use service name in filename)
            zip_path = local_path.parent / self.migration_zip_name
            if zip_path.exists():
                zip_path.unlink()
            return False
    
    def ensure_migrations_exist(self, local_path: Path) -> bool:
        """
        Ensure migration files exist locally, download from Wasabi if missing.
        
        Args:
            local_path: Local directory path to check/store migrations
        
        Returns:
            True if migrations exist locally or were successfully downloaded, False otherwise
        """
        # Check if migrations directory exists and has Python files
        if local_path.exists():
            migration_files = list(local_path.glob("*.py"))
            if migration_files:
                logger.info(
                    f"Migrations already exist locally at {local_path} "
                    f"({len(migration_files)} files)"
                )
                return True
        
        # Migrations don't exist locally, try to download from Wasabi
        logger.info(
            f"Migrations not found locally at {local_path}, "
            "attempting to download from Wasabi..."
        )
        
        if self.download_migrations(local_path):
            return True
        
        # Download failed
        logger.error(
            f"Failed to download migrations from Wasabi. "
            f"Please ensure migrations are uploaded to Wasabi bucket: {self.bucket_name}"
        )
        return False
    
    def list_available_versions(self) -> list[str]:
        """
        List all available migration versions in Wasabi.
        
        Returns:
            List of version strings available in Wasabi
        """
        if not self.s3_client:
            return []
        
        try:
            versions = []
            prefix = "migrations/"
            
            # List all objects with the migrations prefix
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix, Delimiter='/')
            
            for page in pages:
                # Get common prefixes (these are the version directories)
                if 'CommonPrefixes' in page:
                    for prefix_info in page['CommonPrefixes']:
                        # Extract version from path like "migrations/v1.0.0/" or "migrations/latest/"
                        version_path = prefix_info['Prefix']
                        version = version_path.replace(prefix, '').rstrip('/')
                        # Filter to only include actual version directories (not 'latest')
                        if version and version != 'latest':
                            versions.append(version)
                
                # Also check for objects directly (in case structure is different)
                if 'Contents' in page:
                    for obj in page['Contents']:
                        obj_key = obj['Key']
                        # Look for migration zip files with service name pattern
                        if self.migration_zip_name in obj_key:
                            # Extract version from path like "migrations/v1.0.0/service-migrations.zip"
                            parts = obj_key.split('/')
                            if len(parts) >= 3 and parts[0] == 'migrations':
                                version = parts[1]
                                if version not in versions and version != 'latest':
                                    versions.append(version)
            
            return sorted(versions)
        except Exception as e:
            logger.error(f"Error listing migration versions: {str(e)}")
            return []

