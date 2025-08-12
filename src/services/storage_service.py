"""
Storage Service Layer for GITTE system.
Provides abstraction layer for object storage with MinIO and local filesystem fallback.
"""

import logging
import mimetypes
import shutil
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO
from uuid import uuid4

from config.config import config

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Base exception for storage operations."""

    pass


class StorageConnectionError(StorageError):
    """Raised when storage connection fails."""

    pass


class StorageUploadError(StorageError):
    """Raised when file upload fails."""

    pass


class StorageDownloadError(StorageError):
    """Raised when file download fails."""

    pass


class StorageDeleteError(StorageError):
    """Raised when file deletion fails."""

    pass


class StorageProvider(ABC):
    """Abstract base class for storage providers."""

    @abstractmethod
    def upload_file(
        self,
        file_data: bytes | BinaryIO | str,
        object_name: str,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """
        Upload a file to storage.

        Args:
            file_data: File data (bytes, file-like object, or file path)
            object_name: Name/key for the stored object
            content_type: MIME type of the file
            metadata: Additional metadata to store with the file

        Returns:
            str: URL or path to access the uploaded file

        Raises:
            StorageUploadError: If upload fails
        """
        pass

    @abstractmethod
    def download_file(self, object_name: str, local_path: str | None = None) -> bytes | str:
        """
        Download a file from storage.

        Args:
            object_name: Name/key of the stored object
            local_path: Optional local path to save the file

        Returns:
            bytes: File content if local_path is None
            str: Local file path if local_path is provided

        Raises:
            StorageDownloadError: If download fails
        """
        pass

    @abstractmethod
    def delete_file(self, object_name: str) -> bool:
        """
        Delete a file from storage.

        Args:
            object_name: Name/key of the stored object

        Returns:
            bool: True if deletion was successful

        Raises:
            StorageDeleteError: If deletion fails
        """
        pass

    @abstractmethod
    def file_exists(self, object_name: str) -> bool:
        """
        Check if a file exists in storage.

        Args:
            object_name: Name/key of the stored object

        Returns:
            bool: True if file exists
        """
        pass

    @abstractmethod
    def get_file_url(self, object_name: str, expires_in: int = 3600) -> str:
        """
        Get a URL to access the file.

        Args:
            object_name: Name/key of the stored object
            expires_in: URL expiration time in seconds

        Returns:
            str: URL to access the file
        """
        pass

    @abstractmethod
    def get_file_metadata(self, object_name: str) -> dict[str, Any]:
        """
        Get metadata for a stored file.

        Args:
            object_name: Name/key of the stored object

        Returns:
            Dict containing file metadata
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if the storage provider is healthy.

        Returns:
            bool: True if storage is accessible
        """
        pass


class MinIOStorageProvider(StorageProvider):
    """MinIO (S3-compatible) storage provider."""

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        secure: bool = False,
    ):
        """
        Initialize MinIO storage provider.

        Args:
            endpoint: MinIO server endpoint
            access_key: Access key for authentication
            secret_key: Secret key for authentication
            bucket_name: Bucket name for storing files
            secure: Whether to use HTTPS
        """
        try:
            from minio import Minio

            self.endpoint = endpoint
            self.bucket_name = bucket_name
            self.secure = secure

            # Initialize MinIO client
            self.client = Minio(
                endpoint=endpoint, access_key=access_key, secret_key=secret_key, secure=secure
            )

            # Ensure bucket exists
            self._ensure_bucket_exists()

            logger.info(f"MinIO storage provider initialized: {endpoint}/{bucket_name}")

        except ImportError:
            raise StorageConnectionError(
                "MinIO library not installed. Install with: pip install minio"
            )
        except Exception as e:
            raise StorageConnectionError(f"Failed to initialize MinIO client: {e}")

    def _ensure_bucket_exists(self) -> None:
        """Ensure the bucket exists, create if it doesn't."""
        try:

            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created MinIO bucket: {self.bucket_name}")

        except Exception as e:
            raise StorageConnectionError(f"Failed to ensure bucket exists: {e}")

    def upload_file(
        self,
        file_data: bytes | BinaryIO | str,
        object_name: str,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """Upload file to MinIO."""
        try:
            import io

            # Handle different input types
            if isinstance(file_data, str):
                # File path
                file_path = Path(file_data)
                if not file_path.exists():
                    raise StorageUploadError(f"File not found: {file_data}")

                file_size = file_path.stat().st_size
                content_type = (
                    content_type
                    or mimetypes.guess_type(str(file_path))[0]
                    or "application/octet-stream"
                )

                with open(file_path, "rb") as file_obj:
                    self.client.put_object(
                        bucket_name=self.bucket_name,
                        object_name=object_name,
                        data=file_obj,
                        length=file_size,
                        content_type=content_type,
                        metadata=metadata,
                    )

            elif isinstance(file_data, bytes):
                # Bytes data
                file_obj = io.BytesIO(file_data)
                content_type = content_type or "application/octet-stream"

                self.client.put_object(
                    bucket_name=self.bucket_name,
                    object_name=object_name,
                    data=file_obj,
                    length=len(file_data),
                    content_type=content_type,
                    metadata=metadata,
                )

            else:
                # File-like object
                content_type = content_type or "application/octet-stream"

                # Get file size
                current_pos = file_data.tell()
                file_data.seek(0, 2)  # Seek to end
                file_size = file_data.tell()
                file_data.seek(current_pos)  # Restore position

                self.client.put_object(
                    bucket_name=self.bucket_name,
                    object_name=object_name,
                    data=file_data,
                    length=file_size,
                    content_type=content_type,
                    metadata=metadata,
                )

            # Return URL to access the file
            url = f"{'https' if self.secure else 'http'}://{self.endpoint}/{self.bucket_name}/{object_name}"
            logger.debug(f"File uploaded to MinIO: {object_name}")
            return url

        except Exception as e:
            logger.error(f"MinIO upload failed for {object_name}: {e}")
            raise StorageUploadError(f"Failed to upload to MinIO: {e}")

    def download_file(self, object_name: str, local_path: str | None = None) -> bytes | str:
        """Download file from MinIO."""
        try:

            if local_path:
                # Download to local file
                self.client.fget_object(self.bucket_name, object_name, local_path)
                logger.debug(f"File downloaded from MinIO to {local_path}: {object_name}")
                return local_path
            else:
                # Download to memory
                response = self.client.get_object(self.bucket_name, object_name)
                data = response.read()
                response.close()
                response.release_conn()
                logger.debug(f"File downloaded from MinIO to memory: {object_name}")
                return data

        except Exception as e:
            logger.error(f"MinIO download failed for {object_name}: {e}")
            raise StorageDownloadError(f"Failed to download from MinIO: {e}")

    def delete_file(self, object_name: str) -> bool:
        """Delete file from MinIO."""
        try:

            self.client.remove_object(self.bucket_name, object_name)
            logger.debug(f"File deleted from MinIO: {object_name}")
            return True

        except Exception as e:
            logger.error(f"MinIO deletion failed for {object_name}: {e}")
            raise StorageDeleteError(f"Failed to delete from MinIO: {e}")

    def file_exists(self, object_name: str) -> bool:
        """Check if file exists in MinIO."""
        try:
            from minio.error import S3Error

            try:
                self.client.stat_object(self.bucket_name, object_name)
                return True
            except S3Error as e:
                if e.code == "NoSuchKey":
                    return False
                raise

        except Exception as e:
            logger.error(f"MinIO file existence check failed for {object_name}: {e}")
            return False

    def get_file_url(self, object_name: str, expires_in: int = 3600) -> str:
        """Get presigned URL for MinIO object."""
        try:
            from datetime import timedelta

            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=timedelta(seconds=expires_in),
            )
            return url

        except Exception as e:
            logger.error(f"MinIO URL generation failed for {object_name}: {e}")
            # Fallback to direct URL
            return f"{'https' if self.secure else 'http'}://{self.endpoint}/{self.bucket_name}/{object_name}"

    def get_file_metadata(self, object_name: str) -> dict[str, Any]:
        """Get file metadata from MinIO."""
        try:

            stat = self.client.stat_object(self.bucket_name, object_name)

            return {
                "size": stat.size,
                "etag": stat.etag,
                "content_type": stat.content_type,
                "last_modified": stat.last_modified,
                "metadata": stat.metadata or {},
            }

        except Exception as e:
            logger.error(f"MinIO metadata retrieval failed for {object_name}: {e}")
            return {}

    def health_check(self) -> bool:
        """Check MinIO connection health."""
        try:
            # Try to list objects (limit to 1 for efficiency)
            list(self.client.list_objects(self.bucket_name, max_keys=1))
            return True
        except Exception as e:
            logger.error(f"MinIO health check failed: {e}")
            return False


class LocalFileSystemProvider(StorageProvider):
    """Local filesystem storage provider."""

    def __init__(self, base_path: str):
        """
        Initialize local filesystem provider.

        Args:
            base_path: Base directory for storing files
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Local filesystem storage provider initialized: {self.base_path}")

    def _get_full_path(self, object_name: str) -> Path:
        """Get full path for an object."""
        # Ensure object_name doesn't contain path traversal
        safe_name = str(Path(object_name).name)
        return self.base_path / safe_name

    def upload_file(
        self,
        file_data: bytes | BinaryIO | str,
        object_name: str,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """Upload file to local filesystem."""
        try:
            target_path = self._get_full_path(object_name)

            if isinstance(file_data, str):
                # File path - copy file
                source_path = Path(file_data)
                if not source_path.exists():
                    raise StorageUploadError(f"Source file not found: {file_data}")
                shutil.copy2(source_path, target_path)

            elif isinstance(file_data, bytes):
                # Bytes data - write to file
                with open(target_path, "wb") as f:
                    f.write(file_data)

            else:
                # File-like object - copy content
                with open(target_path, "wb") as f:
                    shutil.copyfileobj(file_data, f)

            # Store metadata if provided
            if metadata:
                metadata_path = target_path.with_suffix(target_path.suffix + ".meta")
                import json

                with open(metadata_path, "w") as f:
                    json.dump(metadata, f)

            logger.debug(f"File uploaded to local storage: {target_path}")
            return str(target_path)

        except Exception as e:
            logger.error(f"Local storage upload failed for {object_name}: {e}")
            raise StorageUploadError(f"Failed to upload to local storage: {e}")

    def download_file(self, object_name: str, local_path: str | None = None) -> bytes | str:
        """Download file from local filesystem."""
        try:
            source_path = self._get_full_path(object_name)

            if not source_path.exists():
                raise StorageDownloadError(f"File not found: {object_name}")

            if local_path:
                # Copy to specified location
                shutil.copy2(source_path, local_path)
                logger.debug(f"File copied from local storage to {local_path}: {object_name}")
                return local_path
            else:
                # Read to memory
                with open(source_path, "rb") as f:
                    data = f.read()
                logger.debug(f"File read from local storage to memory: {object_name}")
                return data

        except Exception as e:
            logger.error(f"Local storage download failed for {object_name}: {e}")
            raise StorageDownloadError(f"Failed to download from local storage: {e}")

    def delete_file(self, object_name: str) -> bool:
        """Delete file from local filesystem."""
        try:
            file_path = self._get_full_path(object_name)
            metadata_path = file_path.with_suffix(file_path.suffix + ".meta")

            # Delete main file
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"File deleted from local storage: {file_path}")

            # Delete metadata file if exists
            if metadata_path.exists():
                metadata_path.unlink()
                logger.debug(f"Metadata deleted from local storage: {metadata_path}")

            return True

        except Exception as e:
            logger.error(f"Local storage deletion failed for {object_name}: {e}")
            raise StorageDeleteError(f"Failed to delete from local storage: {e}")

    def file_exists(self, object_name: str) -> bool:
        """Check if file exists in local filesystem."""
        try:
            return self._get_full_path(object_name).exists()
        except Exception as e:
            logger.error(f"Local storage file existence check failed for {object_name}: {e}")
            return False

    def get_file_url(self, object_name: str, expires_in: int = 3600) -> str:
        """Get file URL (local path) for local filesystem."""
        # For local filesystem, return the file path
        # In a web context, this might need to be a served URL
        return str(self._get_full_path(object_name))

    def get_file_metadata(self, object_name: str) -> dict[str, Any]:
        """Get file metadata from local filesystem."""
        try:
            file_path = self._get_full_path(object_name)
            metadata_path = file_path.with_suffix(file_path.suffix + ".meta")

            if not file_path.exists():
                return {}

            stat = file_path.stat()
            metadata = {
                "size": stat.st_size,
                "last_modified": datetime.fromtimestamp(stat.st_mtime),
                "content_type": mimetypes.guess_type(str(file_path))[0]
                or "application/octet-stream",
            }

            # Load custom metadata if exists
            if metadata_path.exists():
                import json

                try:
                    with open(metadata_path) as f:
                        custom_metadata = json.load(f)
                    metadata["metadata"] = custom_metadata
                except Exception as e:
                    logger.warning(f"Failed to load metadata for {object_name}: {e}")
                    metadata["metadata"] = {}
            else:
                metadata["metadata"] = {}

            return metadata

        except Exception as e:
            logger.error(f"Local storage metadata retrieval failed for {object_name}: {e}")
            return {}

    def health_check(self) -> bool:
        """Check local filesystem health."""
        try:
            # Check if base directory is accessible
            return self.base_path.exists() and self.base_path.is_dir()
        except Exception as e:
            logger.error(f"Local storage health check failed: {e}")
            return False


class StorageService:
    """
    Main storage service that provides abstraction over different storage providers.
    Handles provider selection and fallback logic.
    """

    def __init__(
        self, primary_provider: StorageProvider, fallback_provider: StorageProvider | None = None
    ):
        """
        Initialize storage service.

        Args:
            primary_provider: Primary storage provider
            fallback_provider: Optional fallback provider
        """
        self.primary_provider = primary_provider
        self.fallback_provider = fallback_provider

        logger.info(f"Storage service initialized with primary: {type(primary_provider).__name__}")
        if fallback_provider:
            logger.info(f"Fallback provider: {type(fallback_provider).__name__}")

    def _get_active_provider(self) -> StorageProvider:
        """Get the currently active storage provider."""
        if self.primary_provider.health_check():
            return self.primary_provider
        elif self.fallback_provider and self.fallback_provider.health_check():
            logger.warning("Primary storage provider unhealthy, using fallback")
            return self.fallback_provider
        else:
            logger.error("No healthy storage providers available")
            return self.primary_provider  # Try primary anyway

    def upload_file(
        self,
        file_data: bytes | BinaryIO | str,
        object_name: str | None = None,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """
        Upload a file using the active storage provider.

        Args:
            file_data: File data to upload
            object_name: Optional object name (generated if not provided)
            content_type: MIME type of the file
            metadata: Additional metadata

        Returns:
            str: URL or path to access the uploaded file
        """
        if not object_name:
            # Generate unique object name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid4())[:8]

            # Try to determine file extension
            extension = ""
            if isinstance(file_data, str):
                extension = Path(file_data).suffix
            elif content_type:
                import mimetypes

                extension = mimetypes.guess_extension(content_type) or ""

            object_name = f"{timestamp}_{unique_id}{extension}"

        provider = self._get_active_provider()
        return provider.upload_file(file_data, object_name, content_type, metadata)

    def download_file(self, object_name: str, local_path: str | None = None) -> bytes | str:
        """Download a file using the active storage provider."""
        provider = self._get_active_provider()
        return provider.download_file(object_name, local_path)

    def delete_file(self, object_name: str) -> bool:
        """Delete a file using the active storage provider."""
        provider = self._get_active_provider()
        return provider.delete_file(object_name)

    def file_exists(self, object_name: str) -> bool:
        """Check if a file exists using the active storage provider."""
        provider = self._get_active_provider()
        return provider.file_exists(object_name)

    def get_file_url(self, object_name: str, expires_in: int = 3600) -> str:
        """Get file URL using the active storage provider."""
        provider = self._get_active_provider()
        return provider.get_file_url(object_name, expires_in)

    def get_file_metadata(self, object_name: str) -> dict[str, Any]:
        """Get file metadata using the active storage provider."""
        provider = self._get_active_provider()
        return provider.get_file_metadata(object_name)

    def health_check(self) -> dict[str, bool]:
        """Check health of all storage providers."""
        health = {"primary": self.primary_provider.health_check()}

        if self.fallback_provider:
            health["fallback"] = self.fallback_provider.health_check()

        return health

    def get_storage_stats(self) -> dict[str, Any]:
        """Get storage statistics."""
        # This would be implemented based on specific provider capabilities
        # For now, return basic health information
        return {
            "health": self.health_check(),
            "active_provider": type(self._get_active_provider()).__name__,
        }


# Global storage service instance
_storage_service: StorageService | None = None


def get_storage_service() -> StorageService:
    """Get the global storage service instance."""
    global _storage_service

    if _storage_service is None:
        _storage_service = create_storage_service()

    return _storage_service


def set_storage_service(service: StorageService) -> None:
    """Set the global storage service instance."""
    global _storage_service
    _storage_service = service


def create_storage_service() -> StorageService:
    """Create storage service based on configuration."""
    try:
        # Try to create MinIO provider if configured and enabled
        if (
            config.storage.use_minio
            and config.storage.minio_endpoint
            and config.storage.minio_access_key
            and config.storage.minio_secret_key
        ):

            try:
                primary_provider = MinIOStorageProvider(
                    endpoint=config.storage.minio_endpoint,
                    access_key=config.storage.minio_access_key,
                    secret_key=config.storage.minio_secret_key,
                    bucket_name=config.storage.minio_bucket,
                    secure=False,  # Default to False for local development
                )

                # Create local filesystem as fallback
                fallback_provider = LocalFileSystemProvider(
                    base_path=config.storage.local_storage_path
                )

                return StorageService(primary_provider, fallback_provider)

            except StorageConnectionError as e:
                logger.warning(f"Failed to initialize MinIO provider: {e}")
                # Fall through to local filesystem only

        # Use local filesystem as primary
        local_provider = LocalFileSystemProvider(base_path=config.storage.local_storage_path)

        return StorageService(local_provider)

    except Exception as e:
        logger.error(f"Failed to create storage service: {e}")
        # Last resort - use local filesystem with default path
        local_provider = LocalFileSystemProvider("./generated_images")
        return StorageService(local_provider)


# Convenience functions
def upload_file(
    file_data: bytes | BinaryIO | str,
    object_name: str | None = None,
    content_type: str | None = None,
    metadata: dict[str, str] | None = None,
) -> str:
    """Upload a file using the global storage service."""
    return get_storage_service().upload_file(file_data, object_name, content_type, metadata)


def download_file(object_name: str, local_path: str | None = None) -> bytes | str:
    """Download a file using the global storage service."""
    return get_storage_service().download_file(object_name, local_path)


def delete_file(object_name: str) -> bool:
    """Delete a file using the global storage service."""
    return get_storage_service().delete_file(object_name)


def file_exists(object_name: str) -> bool:
    """Check if a file exists using the global storage service."""
    return get_storage_service().file_exists(object_name)


def get_file_url(object_name: str, expires_in: int = 3600) -> str:
    """Get file URL using the global storage service."""
    return get_storage_service().get_file_url(object_name, expires_in)


def get_file_metadata(object_name: str) -> dict[str, Any]:
    """Get file metadata using the global storage service."""
    return get_storage_service().get_file_metadata(object_name)
