# src/services/storage/base.py
from abc import ABC, abstractmethod
from typing import Optional, BinaryIO, Union, List
from pydantic import BaseModel


class FileObject(BaseModel):
    """Represents a file in storage"""
    name: str
    size: int
    content_type: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    metadata: dict = {}


class StorageService(ABC):
    """Abstract base class for storage services"""

    @abstractmethod
    async def upload_file(self,
                          file_data: Union[BinaryIO, bytes, str],
                          destination_path: str,
                          content_type: Optional[str] = None,
                          metadata: Optional[dict] = None) -> str:
        """Upload a file to storage and return its path/URL"""
        pass

    @abstractmethod
    async def download_file(self, file_path: str) -> bytes:
        """Download a file from storage and return its content as bytes"""
        pass

    @abstractmethod
    async def delete_file(self, file_path: str) -> bool:
        """Delete a file from storage"""
        pass

    @abstractmethod
    async def get_file_metadata(self, file_path: str) -> FileObject:
        """Get metadata for a file"""
        pass

    @abstractmethod
    async def generate_signed_url(self,
                                  file_path: str,
                                  expiration: int = 3600) -> str:
        """Generate a signed URL for temporary access to a file"""
        pass

    @abstractmethod
    async def list_files(self,
                         prefix: Optional[str] = None,
                         delimiter: Optional[str] = None) -> List[FileObject]:
        """List files in storage with optional prefix filtering"""
        pass

    @abstractmethod
    async def file_exists(self, file_path: str) -> bool:
        """Check if a file exists in storage"""
        pass
