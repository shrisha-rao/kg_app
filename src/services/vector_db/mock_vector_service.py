# src/services/vector_db/mock_service.py
import logging
from typing import List, Optional, Dict, Any
from .base import VectorDBService

logger = logging.getLogger(__name__)


class MockVectorService(VectorDBService):
    """Mock vector service for development/testing with emulators"""

    def __init__(self):
        logger.info("Initializing Mock Vector Service for development")
        self.vectors = {}
        self.dimension = 768  # Default dimension for mock embeddings

    async def upsert_embeddings(self,
                                vectors: List[List[float]],
                                ids: List[str],
                                metadatas: List[Dict[str, Any]],
                                namespace: Optional[str] = None) -> bool:
        """Mock vector upsert for development"""
        logger.info(
            f"Mock: Upserting {len(vectors)} vectors with namespace: {namespace}"
        )

        for i, (vector, vector_id,
                metadata) in enumerate(zip(vectors, ids, metadatas)):
            # Store the vector with its metadata
            full_id = f"{namespace}_{vector_id}" if namespace else vector_id
            self.vectors[full_id] = {
                "id": vector_id,
                "vector": vector,
                "metadata": {
                    **metadata, "namespace": namespace
                },
                "namespace": namespace
            }
            logger.info(
                f"Mock: Stored vector {vector_id} with {len(vector)} dimensions"
            )

        return True

    async def search(
            self,
            query_embedding: List[float],
            top_k: int,
            namespace: Optional[str] = None,
            filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Mock vector search for development"""
        logger.info(
            f"Mock: Searching with vector of length {len(query_embedding)}, top_k={top_k}, namespace: {namespace}"
        )

        # Filter vectors by namespace if specified
        filtered_vectors = []
        for vector_id, vector_data in self.vectors.items():
            if namespace is None or vector_data.get("namespace") == namespace:
                if filter:
                    # Apply simple filter logic (mock implementation)
                    matches_filter = True
                    for key, value in filter.items():
                        if key in vector_data.get(
                                "metadata",
                            {}) and vector_data["metadata"][key] != value:
                            matches_filter = False
                            break
                    if matches_filter:
                        filtered_vectors.append(vector_data)
                else:
                    filtered_vectors.append(vector_data)

        # Return mock results with similarity scores
        results = []
        for i in range(min(top_k, len(filtered_vectors))):
            vector_data = filtered_vectors[
                i % len(filtered_vectors)]  # Cycle through available vectors
            results.append({
                "id": vector_data["id"],
                "score": 0.9 - (i * 0.1),  # Mock similarity score
                "metadata": vector_data["metadata"]
            })

        # If no vectors found, return mock results
        if not results:
            results = [{
                "id": f"mock_result_{i}",
                "score": 0.9 - (i * 0.1),
                "metadata": {
                    "text": f"Mock result text {i}",
                    "namespace": namespace or "default"
                }
            } for i in range(min(top_k, 5))]

        logger.info(f"Mock: Returning {len(results)} results")
        return results

    async def delete(self,
                     ids: List[str],
                     namespace: Optional[str] = None) -> bool:
        """Mock vector deletion for development"""
        logger.info(
            f"Mock: Deleting {len(ids)} vectors from namespace: {namespace}")

        deleted_count = 0
        for vector_id in ids:
            full_id = f"{namespace}_{vector_id}" if namespace else vector_id
            if full_id in self.vectors:
                del self.vectors[full_id]
                deleted_count += 1
            else:
                # Also try without namespace prefix
                if vector_id in self.vectors:
                    del self.vectors[vector_id]
                    deleted_count += 1

        logger.info(f"Mock: Successfully deleted {deleted_count} vectors")
        return deleted_count > 0

    # Optional: Keep the old method names as aliases for backward compatibility
    async def upsert_vectors(self, vectors: List[Dict[str, Any]]) -> bool:
        """Compatibility method - converts old format to new format"""
        logger.warning(
            "Mock: Using deprecated upsert_vectors method, please update to upsert_embeddings"
        )

        # Convert old format to new format
        vectors_list = []
        ids_list = []
        metadatas_list = []

        for vector_data in vectors:
            vectors_list.append(vector_data.get("vector", []))
            ids_list.append(vector_data.get("id", ""))
            metadatas_list.append(vector_data.get("metadata", {}))

        return await self.upsert_embeddings(vectors_list, ids_list,
                                            metadatas_list)

    async def query_vectors(self,
                            vector: List[float],
                            top_k: int = 10) -> List[Dict[str, Any]]:
        """Compatibility method - converts old format to new format"""
        logger.warning(
            "Mock: Using deprecated query_vectors method, please update to search"
        )
        return await self.search(vector, top_k)

    async def delete_vectors(self, vector_ids: List[str]) -> bool:
        """Compatibility method - converts old format to new format"""
        logger.warning(
            "Mock: Using deprecated delete_vectors method, please update to delete"
        )
        return await self.delete(vector_ids)
