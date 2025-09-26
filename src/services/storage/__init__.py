# src/services/storage/__init__.py
import os
import logging
from .base import StorageService, FileObject
from src.config import settings

logger = logging.getLogger(__name__)


def get_storage_service() -> StorageService:
    """Factory function to get the appropriate Storage service."""

    # Use mock service if we're using emulators (no GCP credentials)
    if settings.use_mock_services or settings.vector_db_type == "mock":
        from .mock_storage import MockStorageService
        logger.info("Using Mock Storage Service (development mode)")
        return MockStorageService()

    # For now, we only have GCP Cloud Storage implementation
    # You can add other implementations in the future (e.g., AWS S3, Azure Blob Storage)
    try:
        from .gcp_cloud_storage import GCPCloudStorageService
        return GCPCloudStorageService()
    except ImportError as e:
        logger.warning(
            f"GCP storage service not available, falling back to mock: {e}")
