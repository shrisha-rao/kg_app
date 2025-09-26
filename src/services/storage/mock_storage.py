# src/services/storage/mock_storage.py
import logging
from typing import Optional, BinaryIO, Union, List
from datetime import datetime
from .base import StorageService, FileObject

logger = logging.getLogger(__name__)


class MockStorageService(StorageService):
    """Mock storage service for development/testing"""

    def __init__(self):
        logger.info("Initializing Mock Storage Service for development")
        self.files = {}
        self.metadata = {}

    async def upload_file(self,
                          file_data: Union[BinaryIO, bytes, str],
                          destination_path: str,
                          content_type: Optional[str] = None,
                          metadata: Optional[dict] = None) -> str:
        """Mock file upload"""
        if isinstance(file_data, bytes):
            content = file_data
        elif isinstance(file_data, str):
            content = file_data.encode('utf-8')
        else:
            # For BinaryIO, read the content
            content = file_data.read()

        logger.info(
            f"Mock: Uploading file to {destination_path}, size: {len(content)} bytes, content_type: {content_type}"
        )

        self.files[destination_path] = content
        self.metadata[destination_path] = {
            "name": destination_path,
            "size": len(content),
            "content_type": content_type or "application/octet-stream",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

        return f"mock://{destination_path}"

    async def download_file(self, file_path: str) -> bytes:
        """Mock file download"""
        logger.info(f"Mock: Downloading file from {file_path}")
        if file_path in self.files:
            return self.files[file_path]
        raise FileNotFoundError(f"File not found: {file_path}")

    async def delete_file(self, file_path: str) -> bool:
        """Mock file deletion"""
        logger.info(f"Mock: Deleting file {file_path}")
        if file_path in self.files:
            del self.files[file_path]
            del self.metadata[file_path]
            return True
        return False

    async def get_file_metadata(self, file_path: str) -> FileObject:
        """Mock file metadata retrieval"""
        logger.info(f"Mock: Getting metadata for {file_path}")
        if file_path in self.metadata:
            meta = self.metadata[file_path]
            return FileObject(**meta)
        raise FileNotFoundError(f"File not found: {file_path}")

    async def generate_signed_url(self,
                                  file_path: str,
                                  expiration: int = 3600) -> str:
        """Mock signed URL generation"""
        logger.info(
            f"Mock: Generating signed URL for {file_path}, expiration: {expiration}s"
        )
        return f"mock://{file_path}?signature=mock&expires={expiration}"

    async def list_files(self,
                         prefix: Optional[str] = None,
                         delimiter: Optional[str] = None) -> List[FileObject]:
        """Mock file listing"""
        logger.info(
            f"Mock: Listing files with prefix: {prefix}, delimiter: {delimiter}"
        )
        results = []
        for file_path, meta in self.metadata.items():
            if prefix is None or file_path.startswith(prefix):
                results.append(FileObject(**meta))
        return results

    async def file_exists(self, file_path: str) -> bool:
        """Mock file existence check"""
        exists = file_path in self.files
        logger.info(f"Mock: Checking if file exists {file_path}: {exists}")
        return exists
