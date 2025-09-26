# src/services/storage/gcp_cloud_storage.py
import logging
from datetime import datetime, timedelta
from typing import Optional, BinaryIO, Union, List
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError, NotFound

from .base import StorageService, FileObject
from src.config import settings

logger = logging.getLogger(__name__)


class GCPCloudStorageService(StorageService):
    """GCP Cloud Storage implementation of the storage service"""

    def __init__(self):
        self.project_id = settings.gcp_project_id
        self.bucket_name = settings.gcs_bucket_name

        # Initialize Cloud Storage client
        self.client = storage.Client(project=self.project_id)
        self.bucket = self.client.bucket(self.bucket_name)

        logger.info(
            f"Initialized GCP Cloud Storage service with bucket: {self.bucket_name}"
        )

    async def upload_file(self,
                          file_data: Union[BinaryIO, bytes, str],
                          destination_path: str,
                          content_type: Optional[str] = None,
                          metadata: Optional[dict] = None) -> str:
        """Upload a file to GCP Cloud Storage"""
        try:
            blob = self.bucket.blob(destination_path)

            # Set content type if provided
            if content_type:
                blob.content_type = content_type

            # Set metadata if provided
            if metadata:
                blob.metadata = metadata

            # Upload the file
            if isinstance(file_data, bytes):
                blob.upload_from_string(file_data, content_type=content_type)
            elif isinstance(file_data, str):
                blob.upload_from_string(file_data, content_type=content_type)
            else:
                blob.upload_from_file(file_data,
                                      rewind=True,
                                      content_type=content_type)

            logger.info(f"Uploaded file to GCS: {destination_path}")
            return f"gs://{self.bucket_name}/{destination_path}"

        except GoogleCloudError as e:
            logger.error(f"Error uploading file to GCS: {e}")
            raise

    async def download_file(self, file_path: str) -> bytes:
        """Download a file from GCP Cloud Storage"""
        try:
            # Remove gs:// prefix if present
            if file_path.startswith("gs://"):
                file_path = file_path[5:].split("/", 1)[1]

            blob = self.bucket.blob(file_path)
            content = blob.download_as_bytes()

            logger.info(f"Downloaded file from GCS: {file_path}")
            return content

        except NotFound:
            logger.error(f"File not found in GCS: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
        except GoogleCloudError as e:
            logger.error(f"Error downloading file from GCS: {e}")
            raise

    async def delete_file(self, file_path: str) -> bool:
        """Delete a file from GCP Cloud Storage"""
        try:
            # Remove gs:// prefix if present
            if file_path.startswith("gs://"):
                file_path = file_path[5:].split("/", 1)[1]

            blob = self.bucket.blob(file_path)
            blob.delete()

            logger.info(f"Deleted file from GCS: {file_path}")
            return True

        except NotFound:
            logger.warning(f"File not found for deletion: {file_path}")
            return False
        except GoogleCloudError as e:
            logger.error(f"Error deleting file from GCS: {e}")
            raise

    async def get_file_metadata(self, file_path: str) -> FileObject:
        """Get metadata for a file in GCP Cloud Storage"""
        try:
            # Remove gs:// prefix if present
            if file_path.startswith("gs://"):
                file_path = file_path[5:].split("/", 1)[1]

            blob = self.bucket.blob(file_path)
            blob.reload()  # Ensure we have the latest metadata

            return FileObject(
                name=blob.name,
                size=blob.size,
                content_type=blob.content_type,
                created_at=blob.time_created.isoformat()
                if blob.time_created else None,
                updated_at=blob.updated.isoformat() if blob.updated else None,
                metadata=blob.metadata or {})

        except NotFound:
            logger.error(f"File not found in GCS: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
        except GoogleCloudError as e:
            logger.error(f"Error getting file metadata from GCS: {e}")
            raise

    async def generate_signed_url(self,
                                  file_path: str,
                                  expiration: int = 3600) -> str:
        """Generate a signed URL for temporary access to a file"""
        try:
            # Remove gs:// prefix if present
            if file_path.startswith("gs://"):
                file_path = file_path[5:].split("/", 1)[1]

            blob = self.bucket.blob(file_path)

            # Generate signed URL
            url = blob.generate_signed_url(
                expiration=timedelta(seconds=expiration), method="GET")

            logger.info(f"Generated signed URL for file: {file_path}")
            return url

        except NotFound:
            logger.error(f"File not found in GCS: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
        except GoogleCloudError as e:
            logger.error(f"Error generating signed URL for GCS file: {e}")
            raise

    async def list_files(self,
                         prefix: Optional[str] = None,
                         delimiter: Optional[str] = None) -> List[FileObject]:
        """List files in GCP Cloud Storage with optional prefix filtering"""
        try:
            blobs = self.bucket.list_blobs(prefix=prefix, delimiter=delimiter)

            files = []
            for blob in blobs:
                files.append(
                    FileObject(name=blob.name,
                               size=blob.size,
                               content_type=blob.content_type,
                               created_at=blob.time_created.isoformat()
                               if blob.time_created else None,
                               updated_at=blob.updated.isoformat()
                               if blob.updated else None,
                               metadata=blob.metadata or {}))

            logger.info(
                f"Listed {len(files)} files from GCS with prefix: {prefix}")
            return files

        except GoogleCloudError as e:
            logger.error(f"Error listing files from GCS: {e}")
            raise

    async def file_exists(self, file_path: str) -> bool:
        """Check if a file exists in GCP Cloud Storage"""
        try:
            # Remove gs:// prefix if present
            if file_path.startswith("gs://"):
                file_path = file_path[5:].split("/", 1)[1]

            blob = self.bucket.blob(file_path)
            exists = blob.exists()

            logger.debug(
                f"Checked file existence in GCS: {file_path} -> {exists}")
            return exists

        except GoogleCloudError as e:
            logger.error(f"Error checking file existence in GCS: {e}")
            raise
