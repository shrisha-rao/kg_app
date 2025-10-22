# src/services/vector_db/local_vector_db.py
import logging
import time
from typing import List, Dict, Any, Optional
import numpy as np
from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector

from .base import VectorDBService
from src.config import settings

logger = logging.getLogger(__name__)


class LocalVectorDBService(VectorDBService):
    """Local Vector DB implementation using Firestore Emulator for development."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client = self._initialize_firestore_client()
        self.collection_name = "vectors"

    def _initialize_firestore_client(self) -> firestore.Client:
        """Initialize Firestore client with emulator settings."""
        try:
            # For emulator, we don't need credentials
            client = firestore.Client(
                project=settings.gcp_project_id or "dev-project")

            # Test connection
            collections = client.collections()
            self.logger.info("Successfully connected to Firestore Emulator")
            return client

        except Exception as e:
            self.logger.error(
                f"Failed to initialize Firestore client: {str(e)}")
            raise

    async def upsert_embeddings(self,
                                vectors: List[List[float]],
                                ids: List[str],
                                metadatas: List[Dict[str, Any]],
                                namespace: Optional[str] = None):
        """Upsert embeddings into Firestore with vector support."""
        if len(vectors) != len(ids) or len(vectors) != len(metadatas):
            raise ValueError(
                "Vectors, IDs, and metadatas must have the same length")

        batch_size = settings.matching_engine_batch_size or 100
        results = []

        for i in range(0, len(vectors), batch_size):
            batch_vectors = vectors[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]

            try:
                batch = self.client.batch()
                collection_ref = self.client.collection(self.collection_name)

                for vector, doc_id, metadata in zip(batch_vectors, batch_ids,
                                                    batch_metadatas):
                    # Create document data with vector field
                    doc_data = {
                        "vector": Vector(vector),
                        "metadata": metadata,
                        "namespace": namespace or "default",
                        "created_at": firestore.SERVER_TIMESTAMP,
                        "updated_at": firestore.SERVER_TIMESTAMP
                    }

                    # Use the provided ID as document ID
                    doc_ref = collection_ref.document(doc_id)
                    batch.set(doc_ref, doc_data)

                # Commit the batch
                batch.commit()

                self.logger.info(
                    f"Upserted batch of {len(batch_vectors)} vectors to Firestore"
                )
                results.extend([{
                    "status": "success",
                    "id": idx
                } for idx in batch_ids])

                # Rate limiting
                time.sleep(1 / (settings.matching_engine_rps_limit or 10))

            except Exception as e:
                self.logger.error(
                    f"Error upserting batch {i}-{i+batch_size}: {str(e)}")
                results.extend([{
                    "status": "error",
                    "id": idx,
                    "error": str(e)
                } for idx in batch_ids])

        return results

    async def search(
            self,
            query_embedding: List[float],
            top_k: int,
            namespace: Optional[str] = None,
            filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search for similar vectors using cosine similarity."""
        try:
            # Get all vectors from the collection (or filtered by namespace)
            collection_ref = self.client.collection(self.collection_name)

            # Build query
            query = collection_ref

            if namespace:
                query = query.where("namespace", "==", namespace)

            if filter:
                for key, value in filter.items():
                    if isinstance(value, list):
                        query = query.where(key, "in", value)
                    else:
                        query = query.where(key, "==", value)

            # Execute query
            docs = query.stream()

            # Convert to list and calculate similarities
            results = []
            query_vec = np.array(query_embedding)

            for doc in docs:
                doc_data = doc.to_dict()
                vector_data = doc_data.get("vector")

                if vector_data:
                    # Convert Firestore Vector to numpy array
                    doc_vec = np.array(vector_data)

                    # Calculate cosine similarity
                    similarity = self._cosine_similarity(query_vec, doc_vec)

                    results.append({
                        "id": doc.id,
                        "score": similarity,
                        "metadata": doc_data.get("metadata", {}),
                        "distance":
                        1 - similarity  # Convert similarity to distance
                    })

            # Sort by similarity (descending) and take top_k
            results.sort(key=lambda x: x["score"], reverse=True)
            top_results = results[:top_k]

            # Format results to match Vertex AI format
            formatted_results = []
            for result in top_results:
                formatted_results.append({
                    "id": result["id"],
                    "distance": result["distance"],
                    "metadata": result["metadata"]
                })

            return formatted_results

        except Exception as e:
            self.logger.error(f"Error searching Firestore: {str(e)}")
            raise

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
            return 0.0

        return np.dot(vec1,
                      vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

    async def delete(self, ids: List[str], namespace: Optional[str] = None):
        """Delete vectors by IDs."""
        if not ids:
            return []

        batch_size = settings.matching_engine_batch_size or 100
        results = []

        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]

            try:
                batch = self.client.batch()
                collection_ref = self.client.collection(self.collection_name)

                for doc_id in batch_ids:
                    doc_ref = collection_ref.document(doc_id)
                    batch.delete(doc_ref)

                batch.commit()

                results.extend([{
                    "status": "success",
                    "id": idx
                } for idx in batch_ids])

                # Rate limiting
                time.sleep(1 / (settings.matching_engine_rps_limit or 10))

            except Exception as e:
                self.logger.error(
                    f"Error deleting batch {i}-{i+batch_size}: {str(e)}")
                results.extend([{
                    "status": "error",
                    "id": idx,
                    "error": str(e)
                } for idx in batch_ids])

        return results

    async def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector collection."""
        try:
            collection_ref = self.client.collection(self.collection_name)
            docs = collection_ref.stream()

            count = 0
            namespaces = set()

            for doc in docs:
                count += 1
                doc_data = doc.to_dict()
                namespace = doc_data.get("namespace", "unknown")
                namespaces.add(namespace)

            return {
                "vectors_count": count,
                "namespaces": list(namespaces),
                "shards_count": 1,  # Firestore doesn't use shards
                "collection_name": self.collection_name
            }

        except Exception as e:
            self.logger.error(f"Error getting index stats: {str(e)}")
            return {"error": str(e)}
