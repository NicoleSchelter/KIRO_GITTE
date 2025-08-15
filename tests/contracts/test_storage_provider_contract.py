"""
Contract tests for storage providers.
Tests that all storage providers implement the same interface correctly.
"""

import io
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from uuid import uuid4

import pytest

from src.services.storage_service import (
    LocalFileSystemProvider,
    MinIOStorageProvider,
    StorageProvider,
)


class StorageProviderContract(ABC):
    """Contract that all storage providers must satisfy."""
    
    @abstractmethod
    def create_provider(self) -> StorageProvider:
        """Create a storage provider instance for testing."""
        pass
    
    @abstractmethod
    def cleanup_provider(self, provider: StorageProvider):
        """Clean up after testing."""
        pass
    
    def test_upload_and_download_bytes(self):
        """Test uploading and downloading bytes data."""
        provider = self.create_provider()
        try:
            test_data = b"Hello, World!"
            object_name = f"test_file_{uuid4().hex[:8]}.txt"
            
            # Upload
            result = provider.upload_file(test_data, object_name)
            assert result is not None
            
            # Download
            downloaded = provider.download_file(object_name)
            assert downloaded == test_data
            
            # Check existence
            assert provider.file_exists(object_name) is True
            
            # Clean up
            provider.delete_file(object_name)
            assert provider.file_exists(object_name) is False
            
        finally:
            self.cleanup_provider(provider)
    
    def test_upload_from_file_path(self):
        """Test uploading from file path."""
        provider = self.create_provider()
        try:
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                test_data = b"File path test content"
                temp_file.write(test_data)
                temp_file.flush()
                
                object_name = f"path_test_{uuid4().hex[:8]}.txt"
                
                # Upload from path
                result = provider.upload_file(temp_file.name, object_name)
                assert result is not None
                
                # Verify content
                downloaded = provider.download_file(object_name)
                assert downloaded == test_data
                
                # Clean up
                provider.delete_file(object_name)
                import contextlib
                with contextlib.suppress(PermissionError, OSError):
                    # Windows may have file handle issues
                    Path(temp_file.name).unlink()
                
        finally:
            self.cleanup_provider(provider)
    
    def test_upload_from_file_object(self):
        """Test uploading from file-like object."""
        provider = self.create_provider()
        try:
            test_data = b"File object test content"
            file_obj = io.BytesIO(test_data)
            object_name = f"fileobj_test_{uuid4().hex[:8]}.txt"
            
            # Upload from file object
            result = provider.upload_file(file_obj, object_name)
            assert result is not None
            
            # Verify content
            downloaded = provider.download_file(object_name)
            assert downloaded == test_data
            
            # Clean up
            provider.delete_file(object_name)
            
        finally:
            self.cleanup_provider(provider)
    
    def test_upload_with_metadata(self):
        """Test uploading with metadata."""
        provider = self.create_provider()
        try:
            test_data = b"Metadata test content"
            object_name = f"meta_test_{uuid4().hex[:8]}.txt"
            metadata = {"author": "test", "version": "1.0"}
            
            # Upload with metadata
            provider.upload_file(test_data, object_name, metadata=metadata)
            
            # Check metadata (if supported)
            try:
                file_metadata = provider.get_file_metadata(object_name)
                if "metadata" in file_metadata:
                    assert file_metadata["metadata"] == metadata
            except NotImplementedError:
                # Some providers might not support metadata
                pass
            
            # Clean up
            provider.delete_file(object_name)
            
        finally:
            self.cleanup_provider(provider)
    
    def test_download_to_file(self):
        """Test downloading to file."""
        provider = self.create_provider()
        try:
            test_data = b"Download to file test"
            object_name = f"download_test_{uuid4().hex[:8]}.txt"
            
            # Upload first
            provider.upload_file(test_data, object_name)
            
            # Download to file
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                result = provider.download_file(object_name, temp_file.name)
                assert result == temp_file.name
                
                # Verify content
                assert Path(temp_file.name).read_bytes() == test_data
                
                # Clean up
                import contextlib
                with contextlib.suppress(PermissionError, OSError):
                    # Windows may have file handle issues
                    Path(temp_file.name).unlink()
            
            provider.delete_file(object_name)
            
        finally:
            self.cleanup_provider(provider)
    
    def test_file_operations(self):
        """Test basic file operations."""
        provider = self.create_provider()
        try:
            test_data = b"File operations test"
            object_name = f"ops_test_{uuid4().hex[:8]}.txt"
            
            # File should not exist initially
            assert provider.file_exists(object_name) is False
            
            # Upload
            provider.upload_file(test_data, object_name)
            assert provider.file_exists(object_name) is True
            
            # Get metadata
            try:
                metadata = provider.get_file_metadata(object_name)
                assert metadata["size"] == len(test_data)
                assert "last_modified" in metadata
            except NotImplementedError:
                # Some providers might not support metadata
                pass
            
            # Delete
            provider.delete_file(object_name)
            assert provider.file_exists(object_name) is False
            
        finally:
            self.cleanup_provider(provider)
    
    def test_health_check(self):
        """Test provider health check."""
        provider = self.create_provider()
        try:
            # Health check should return boolean
            health = provider.health_check()
            assert isinstance(health, bool)
            
        finally:
            self.cleanup_provider(provider)


class TestLocalFileSystemProviderContract(StorageProviderContract):
    """Contract tests for LocalFileSystemProvider."""
    
    def create_provider(self) -> StorageProvider:
        """Create a local filesystem provider for testing."""
        temp_dir = tempfile.mkdtemp()
        return LocalFileSystemProvider(base_path=temp_dir)
    
    def cleanup_provider(self, provider: StorageProvider):
        """Clean up temporary directory."""
        if hasattr(provider, 'base_path'):
            import shutil
            shutil.rmtree(provider.base_path, ignore_errors=True)


# Note: MinIO contract tests would require a running MinIO instance
# For now, we'll skip them in CI but they can be run manually
@pytest.mark.skip(reason="Requires running MinIO instance")
class TestMinIOProviderContract(StorageProviderContract):
    """Contract tests for MinIOStorageProvider."""
    
    def create_provider(self) -> StorageProvider:
        """Create a MinIO provider for testing."""
        # This would require a test MinIO instance
        return MinIOStorageProvider(
            endpoint="localhost:9000",
            access_key="test_key",
            secret_key="test_secret",
            bucket_name="test-bucket",
            secure=False
        )
    
    def cleanup_provider(self, provider: StorageProvider):
        """Clean up MinIO test data."""
        # Clean up test objects if needed
        pass


