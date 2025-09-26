#src/services/vector_db/vector_metadata_service.py
import logging
from typing import Dict, Any, List, Optional
from google.cloud import firestore
from src.config import settings


class VectorMetadataService:
    """Service to store and retrieve metadata for vectors."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db = firestore.Client(project=settings.gcp_project_id)
        self.collection = self.db.collection("vector_metadata")

    async def store_metadata(self,
                             vector_id: str,
                             metadata: Dict[str, Any],
                             namespace: Optional[str] = None):
        """Store metadata for a vector."""
        try:
            doc_ref = self.collection.document(vector_id)
            doc_data = {
                "metadata": metadata,
                "namespace": namespace,
                "updated_at": firestore.SERVER_TIMESTAMP
            }
            doc_ref.set(doc_data, merge=True)
        except Exception as e:
            self.logger.error(
                f"Error storing metadata for {vector_id}: {str(e)}")
            raise

    async def get_metadata(self, vector_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a vector."""
        try:
            doc_ref = self.collection.document(vector_id)
            doc = doc_ref.get()
            if doc.exists:
                return doc.to_dict().get("metadata", {})
            return None
        except Exception as e:
            self.logger.error(
                f"Error getting metadata for {vector_id}: {str(e)}")
            return None

    async def batch_get_metadata(
            self, vector_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get metadata for multiple vectors."""
        try:
            results = {}
            for vector_id in vector_ids:
                metadata = await self.get_metadata(vector_id)
                if metadata:
                    results[vector_id] = metadata
            return results
        except Exception as e:
            self.logger.error(f"Error batch getting metadata: {str(e)}")
            return {}

    async def delete_metadata(self, vector_id: str):
        """Delete metadata for a vector."""
        try:
            doc_ref = self.collection.document(vector_id)
            doc_ref.delete()
        except Exception as e:
            self.logger.error(
                f"Error deleting metadata for {vector_id}: {str(e)}")
            raise
