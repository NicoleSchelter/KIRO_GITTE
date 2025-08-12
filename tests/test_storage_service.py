"""
Tests for storage service functionality.
"""

import io
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.services.storage_service import (
    LocalFileSystemProvider,
    MinIOStorageProvider,
    StorageDownloadError,
    StorageService,
    StorageUploadError,
    create_storage_service,
    get_storage_service,
    set_storage_service,
)


class TestLocalFileSystemProvider:
    """Test local filesystem storage provider."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def provider(self, temp_dir):
        """Create local filesystem provider."""
        return LocalFileSystemProvider(temp_dir)

    def test_provider_initialization(self, temp_dir):
        """Test provider initialization."""
        provider = LocalFileSystemProvider(temp_dir)
        assert provider.base_path == Path(temp_dir)
        assert provider.base_path.exists()

    def test_upload_file_bytes(self, provider):
        """Test uploading bytes data."""
        test_data = b"Hello, World!"
        object_name = "test_file.txt"

        result = provider.upload_file(test_data, object_name)

        assert result == str(provider._get_full_path(object_name))
        assert provider.file_exists(object_name)

        # Verify content
        downloaded = provider.download_file(object_name)
        assert downloaded == test_data

    def test_upload_file_from_path(self, provider, temp_dir):
        """Test uploading from file path."""
        # Create source file
        source_file = Path(temp_dir) / "source.txt"
        test_data = b"Test content"
        source_file.write_bytes(test_data)

        object_name = "uploaded_file.txt"
        result = provider.upload_file(str(source_file), object_name)

        assert result == str(provider._get_full_path(object_name))
        assert provider.file_exists(object_name)

        # Verify content
        downloaded = provider.download_file(object_name)
        assert downloaded == test_data

    def test_upload_file_from_fileobj(self, provider):
        """Test uploading from file-like object."""
        test_data = b"File object content"
        file_obj = io.BytesIO(test_data)
        object_name = "fileobj_test.txt"

        result = provider.upload_file(file_obj, object_name)

        assert result == str(provider._get_full_path(object_name))
        assert provider.file_exists(object_name)

        # Verify content
        downloaded = provider.download_file(object_name)
        assert downloaded == test_data

    def test_upload_with_metadata(self, provider):
        """Test uploading with metadata."""
        test_data = b"Content with metadata"
        object_name = "meta_test.txt"
        metadata = {"author": "test", "version": "1.0"}

        provider.upload_file(test_data, object_name, metadata=metadata)

        # Check metadata
        file_metadata = provider.get_file_metadata(object_name)
        assert file_metadata["metadata"] == metadata

    def test_download_to_memory(self, provider):
        """Test downloading to memory."""
        test_data = b"Download test"
        object_name = "download_test.txt"

        provider.upload_file(test_data, object_name)
        downloaded = provider.download_file(object_name)

        assert downloaded == test_data

    def test_download_to_file(self, provider, temp_dir):
        """Test downloading to file."""
        test_data = b"Download to file test"
        object_name = "download_file_test.txt"
        target_path = str(Path(temp_dir) / "downloaded.txt")

        provider.upload_file(test_data, object_name)
        result = provider.download_file(object_name, target_path)

        assert result == target_path
        assert Path(target_path).read_bytes() == test_data

    def test_delete_file(self, provider):
        """Test file deletion."""
        test_data = b"Delete test"
        object_name = "delete_test.txt"

        provider.upload_file(test_data, object_name)
        assert provider.file_exists(object_name)

        result = provider.delete_file(object_name)
        assert result is True
        assert not provider.file_exists(object_name)

    def test_file_exists(self, provider):
        """Test file existence check."""
        object_name = "exists_test.txt"

        assert not provider.file_exists(object_name)

        provider.upload_file(b"test", object_name)
        assert provider.file_exists(object_name)

    def test_get_file_url(self, provider):
        """Test getting file URL."""
        object_name = "url_test.txt"
        provider.upload_file(b"test", object_name)

        url = provider.get_file_url(object_name)
        assert url == str(provider._get_full_path(object_name))

    def test_get_file_metadata(self, provider):
        """Test getting file metadata."""
        test_data = b"Metadata test"
        object_name = "metadata_test.txt"
        metadata = {"key": "value"}

        provider.upload_file(test_data, object_name, metadata=metadata)

        file_metadata = provider.get_file_metadata(object_name)
        assert file_metadata["size"] == len(test_data)
        assert "last_modified" in file_metadata
        assert file_metadata["metadata"] == metadata

    def test_health_check(self, provider):
        """Test health check."""
        assert provider.health_check() is True

    def test_upload_nonexistent_file(self, provider):
        """Test uploading nonexistent file raises error."""
        with pytest.raises(StorageUploadError):
            provider.upload_file("/nonexistent/file.txt", "test.txt")

    def test_download_nonexistent_file(self, provider):
        """Test downloading nonexistent file raises error."""
        with pytest.raises(StorageDownloadError):
            provider.download_file("nonexistent.txt")


class TestMinIOStorageProvider:
    """Test MinIO storage provider."""

    @pytest.fixture
    def mock_minio_client(self):
        """Create mock MinIO client."""
        with patch("src.services.storage_service.Minio") as mock_minio:
            mock_client = Mock()
            mock_minio.return_value = mock_client
            mock_client.bucket_exists.return_value = True
            yield mock_client

    @pytest.fixture
    def provider(self, mock_minio_client):
        """Create MinIO provider with mocked client."""
        with patch("src.services.storage_service.Minio"):
            provider = MinIOStorageProvider(
                endpoint="localhost:9000",
                access_key="test_key",
                secret_key="test_secret",
                bucket_name="test-bucket",
            )
            provider.client = mock_minio_client
            return provider

    def test_provider_initialization(self, mock_minio_client):
        """Test MinIO provider initialization."""
        with patch("src.services.storage_service.Minio") as mock_minio:
            mock_minio.return_value = mock_minio_client
            mock_minio_client.bucket_exists.return_value = True

            provider = MinIOStorageProvider(
                endpoint="localhost:9000",
                access_key="test_key",
                secret_key="test_secret",
                bucket_name="test-bucket",
            )

            assert provider.endpoint == "localhost:9000"
            assert provider.bucket_name == "test-bucket"
            mock_minio_client.bucket_exists.assert_called_once_with("test-bucket")

    def test_bucket_creation(self, mock_minio_client):
        """Test bucket creation when it doesn't exist."""
        with patch("src.services.storage_service.Minio") as mock_minio:
            mock_minio.return_value = mock_minio_client
            mock_minio_client.bucket_exists.return_value = False

            MinIOStorageProvider(
                endpoint="localhost:9000",
                access_key="test_key",
                secret_key="test_secret",
                bucket_name="test-bucket",
            )

            mock_minio_client.make_bucket.assert_called_once_with("test-bucket")

    def test_upload_file_bytes(self, provider, mock_minio_client):
        """Test uploading bytes to MinIO."""
        test_data = b"MinIO test data"
        object_name = "test_file.txt"

        result = provider.upload_file(test_data, object_name)

        assert "test-bucket/test_file.txt" in result
        mock_minio_client.put_object.assert_called_once()

        # Check call arguments
        call_args = mock_minio_client.put_object.call_args
        assert call_args[1]["bucket_name"] == "test-bucket"
        assert call_args[1]["object_name"] == object_name
        assert call_args[1]["length"] == len(test_data)

    def test_upload_file_from_path(self, provider, mock_minio_client, tmp_path):
        """Test uploading file from path to MinIO."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_data = b"File path test"
        test_file.write_bytes(test_data)

        object_name = "uploaded.txt"
        result = provider.upload_file(str(test_file), object_name)

        assert "test-bucket/uploaded.txt" in result
        mock_minio_client.put_object.assert_called_once()

    def test_download_file_to_memory(self, provider, mock_minio_client):
        """Test downloading file to memory from MinIO."""
        test_data = b"Download test"
        object_name = "download_test.txt"

        # Mock response
        mock_response = Mock()
        mock_response.read.return_value = test_data
        mock_minio_client.get_object.return_value = mock_response

        result = provider.download_file(object_name)

        assert result == test_data
        mock_minio_client.get_object.assert_called_once_with("test-bucket", object_name)
        mock_response.close.assert_called_once()
        mock_response.release_conn.assert_called_once()

    def test_download_file_to_path(self, provider, mock_minio_client):
        """Test downloading file to local path from MinIO."""
        object_name = "download_test.txt"
        local_path = "/tmp/downloaded.txt"

        result = provider.download_file(object_name, local_path)

        assert result == local_path
        mock_minio_client.fget_object.assert_called_once_with(
            "test-bucket", object_name, local_path
        )

    def test_delete_file(self, provider, mock_minio_client):
        """Test deleting file from MinIO."""
        object_name = "delete_test.txt"

        result = provider.delete_file(object_name)

        assert result is True
        mock_minio_client.remove_object.assert_called_once_with("test-bucket", object_name)

    def test_file_exists_true(self, provider, mock_minio_client):
        """Test file exists check when file exists."""
        object_name = "exists_test.txt"
        mock_stat = Mock()
        mock_minio_client.stat_object.return_value = mock_stat

        result = provider.file_exists(object_name)

        assert result is True
        mock_minio_client.stat_object.assert_called_once_with("test-bucket", object_name)

    def test_file_exists_false(self, provider, mock_minio_client):
        """Test file exists check when file doesn't exist."""
        from minio.error import S3Error

        object_name = "nonexistent.txt"
        error = S3Error(
            "NoSuchKey", "The specified key does not exist.", "NoSuchKey", "", "", "", ""
        )
        mock_minio_client.stat_object.side_effect = error

        with patch("src.services.storage_service.S3Error", S3Error):
            result = provider.file_exists(object_name)

        assert result is False

    def test_get_file_url(self, provider, mock_minio_client):
        """Test getting presigned URL."""
        object_name = "url_test.txt"
        expected_url = "https://localhost:9000/test-bucket/url_test.txt?signature=..."
        mock_minio_client.presigned_get_object.return_value = expected_url

        result = provider.get_file_url(object_name)

        assert result == expected_url
        mock_minio_client.presigned_get_object.assert_called_once()

    def test_get_file_metadata(self, provider, mock_minio_client):
        """Test getting file metadata."""
        object_name = "metadata_test.txt"

        mock_stat = Mock()
        mock_stat.size = 1024
        mock_stat.etag = "abc123"
        mock_stat.content_type = "text/plain"
        mock_stat.last_modified = "2024-01-01T00:00:00Z"
        mock_stat.metadata = {"custom": "value"}
        mock_minio_client.stat_object.return_value = mock_stat

        result = provider.get_file_metadata(object_name)

        assert result["size"] == 1024
        assert result["etag"] == "abc123"
        assert result["content_type"] == "text/plain"
        assert result["metadata"] == {"custom": "value"}

    def test_health_check_success(self, provider, mock_minio_client):
        """Test successful health check."""
        mock_minio_client.list_objects.return_value = []

        result = provider.health_check()

        assert result is True
        mock_minio_client.list_objects.assert_called_once_with("test-bucket", max_keys=1)

    def test_health_check_failure(self, provider, mock_minio_client):
        """Test failed health check."""
        mock_minio_client.list_objects.side_effect = Exception("Connection failed")

        result = provider.health_check()

        assert result is False


class TestStorageService:
    """Test main storage service."""

    @pytest.fixture
    def mock_primary_provider(self):
        """Create mock primary provider."""
        provider = Mock()
        provider.health_check.return_value = True
        return provider

    @pytest.fixture
    def mock_fallback_provider(self):
        """Create mock fallback provider."""
        provider = Mock()
        provider.health_check.return_value = True
        return provider

    @pytest.fixture
    def storage_service(self, mock_primary_provider, mock_fallback_provider):
        """Create storage service with mock providers."""
        return StorageService(mock_primary_provider, mock_fallback_provider)

    def test_service_initialization(self, mock_primary_provider, mock_fallback_provider):
        """Test storage service initialization."""
        service = StorageService(mock_primary_provider, mock_fallback_provider)

        assert service.primary_provider == mock_primary_provider
        assert service.fallback_provider == mock_fallback_provider

    def test_get_active_provider_primary_healthy(self, storage_service, mock_primary_provider):
        """Test getting active provider when primary is healthy."""
        mock_primary_provider.health_check.return_value = True

        provider = storage_service._get_active_provider()

        assert provider == mock_primary_provider

    def test_get_active_provider_fallback(
        self, storage_service, mock_primary_provider, mock_fallback_provider
    ):
        """Test getting active provider when primary is unhealthy."""
        mock_primary_provider.health_check.return_value = False
        mock_fallback_provider.health_check.return_value = True

        provider = storage_service._get_active_provider()

        assert provider == mock_fallback_provider

    def test_upload_file_with_generated_name(self, storage_service, mock_primary_provider):
        """Test uploading file with auto-generated name."""
        test_data = b"Test data"
        expected_url = "http://example.com/file.txt"
        mock_primary_provider.upload_file.return_value = expected_url

        result = storage_service.upload_file(test_data)

        assert result == expected_url
        mock_primary_provider.upload_file.assert_called_once()

        # Check that object name was generated
        call_args = mock_primary_provider.upload_file.call_args
        object_name = call_args[0][1]
        assert len(object_name) > 0
        assert "_" in object_name  # Should contain timestamp and UUID

    def test_upload_file_with_custom_name(self, storage_service, mock_primary_provider):
        """Test uploading file with custom name."""
        test_data = b"Test data"
        object_name = "custom_file.txt"
        expected_url = "http://example.com/custom_file.txt"
        mock_primary_provider.upload_file.return_value = expected_url

        result = storage_service.upload_file(test_data, object_name)

        assert result == expected_url
        mock_primary_provider.upload_file.assert_called_once_with(
            test_data, object_name, None, None
        )

    def test_download_file(self, storage_service, mock_primary_provider):
        """Test downloading file."""
        object_name = "test_file.txt"
        expected_data = b"File content"
        mock_primary_provider.download_file.return_value = expected_data

        result = storage_service.download_file(object_name)

        assert result == expected_data
        mock_primary_provider.download_file.assert_called_once_with(object_name, None)

    def test_delete_file(self, storage_service, mock_primary_provider):
        """Test deleting file."""
        object_name = "test_file.txt"
        mock_primary_provider.delete_file.return_value = True

        result = storage_service.delete_file(object_name)

        assert result is True
        mock_primary_provider.delete_file.assert_called_once_with(object_name)

    def test_file_exists(self, storage_service, mock_primary_provider):
        """Test checking file existence."""
        object_name = "test_file.txt"
        mock_primary_provider.file_exists.return_value = True

        result = storage_service.file_exists(object_name)

        assert result is True
        mock_primary_provider.file_exists.assert_called_once_with(object_name)

    def test_get_file_url(self, storage_service, mock_primary_provider):
        """Test getting file URL."""
        object_name = "test_file.txt"
        expected_url = "http://example.com/test_file.txt"
        mock_primary_provider.get_file_url.return_value = expected_url

        result = storage_service.get_file_url(object_name)

        assert result == expected_url
        mock_primary_provider.get_file_url.assert_called_once_with(object_name, 3600)

    def test_get_file_metadata(self, storage_service, mock_primary_provider):
        """Test getting file metadata."""
        object_name = "test_file.txt"
        expected_metadata = {"size": 1024, "content_type": "text/plain"}
        mock_primary_provider.get_file_metadata.return_value = expected_metadata

        result = storage_service.get_file_metadata(object_name)

        assert result == expected_metadata
        mock_primary_provider.get_file_metadata.assert_called_once_with(object_name)

    def test_health_check(self, storage_service, mock_primary_provider, mock_fallback_provider):
        """Test health check."""
        mock_primary_provider.health_check.return_value = True
        mock_fallback_provider.health_check.return_value = False

        result = storage_service.health_check()

        expected = {"primary": True, "fallback": False}
        assert result == expected

    def test_get_storage_stats(self, storage_service, mock_primary_provider):
        """Test getting storage statistics."""
        mock_primary_provider.health_check.return_value = True

        result = storage_service.get_storage_stats()

        assert "health" in result
        assert "active_provider" in result
        assert result["health"]["primary"] is True


class TestGlobalStorageService:
    """Test global storage service functions."""

    def test_get_storage_service_singleton(self):
        """Test that get_storage_service returns singleton."""
        # Clear any existing instance
        set_storage_service(None)

        service1 = get_storage_service()
        service2 = get_storage_service()

        assert service1 is service2

    def test_set_storage_service(self):
        """Test setting custom storage service."""
        mock_service = Mock()
        set_storage_service(mock_service)

        result = get_storage_service()
        assert result is mock_service

    @patch("src.services.storage_service.config")
    def test_create_storage_service_with_minio(self, mock_config):
        """Test creating storage service with MinIO configuration."""
        # Mock configuration
        mock_config.storage.use_minio = True
        mock_config.storage.minio_endpoint = "localhost:9000"
        mock_config.storage.minio_access_key = "test_key"
        mock_config.storage.minio_secret_key = "test_secret"
        mock_config.storage.minio_bucket = "test-bucket"
        mock_config.storage.local_storage_path = "./test_images"

        with patch("src.services.storage_service.MinIOStorageProvider") as mock_minio:
            with patch("src.services.storage_service.LocalFileSystemProvider") as mock_local:
                mock_minio_instance = Mock()
                mock_local_instance = Mock()
                mock_minio.return_value = mock_minio_instance
                mock_local.return_value = mock_local_instance

                service = create_storage_service()

                assert isinstance(service, StorageService)
                mock_minio.assert_called_once_with(
                    endpoint="localhost:9000",
                    access_key="test_key",
                    secret_key="test_secret",
                    bucket_name="test-bucket",
                    secure=False,
                )
                mock_local.assert_called_once_with(base_path="./test_images")

    @patch("src.services.storage_service.config")
    def test_create_storage_service_local_only(self, mock_config):
        """Test creating storage service with local filesystem only."""
        # Mock configuration without MinIO
        mock_config.storage.use_minio = False
        mock_config.storage.local_storage_path = "./test_images"

        with patch("src.services.storage_service.LocalFileSystemProvider") as mock_local:
            mock_local_instance = Mock()
            mock_local.return_value = mock_local_instance

            service = create_storage_service()

            assert isinstance(service, StorageService)
            mock_local.assert_called_once_with(base_path="./test_images")
