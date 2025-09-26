#src/services/vector_db/vertex_ai_matching_engine_with_metadata.py
import logging
from typing import List, Dict, Any, Optional
from .vertex_ai_matching_engine import VertexAIMatchingEngineService
from .vector_metadata_service import VectorMetadataService


class VertexAIMatchingEngineWithMetadataService(VertexAIMatchingEngineService):
    """Enhanced Matching Engine service that handles metadata storage."""

    def __init__(self):
        super().__init__()
        self.metadata_service = VectorMetadataService()

    async def upsert_embeddings(self,
                                vectors: List[List[float]],
                                ids: List[str],
                                metadatas: List[Dict[str, Any]],
                                namespace: Optional[str] = None):
        """Upsert embeddings with metadata storage."""
        # Store metadata first
        metadata_results = []
        for idx, metadata in zip(ids, metadatas):
            try:
                await self.metadata_service.store_metadata(
                    idx, metadata, namespace)
                metadata_results.append({"status": "success", "id": idx})
            except Exception as e:
                metadata_results.append({
                    "status": "error",
                    "id": idx,
                    "error": str(e)
                })

        # Then upsert vectors to Matching Engine
        vector_results = await super().upsert_embeddings(
            vectors, ids, metadatas, namespace)

        # Combine results
        combined_results = []
        for vec_res, meta_res in zip(vector_results, metadata_results):
            combined = {
                "id": vec_res["id"],
                "vector_status": vec_res["status"],
                "metadata_status": meta_res["status"]
            }
            if vec_res["status"] == "error":
                combined["vector_error"] = vec_res.get("error")
            if meta_res["status"] == "error":
                combined["metadata_error"] = meta_res.get("error")
            combined_results.append(combined)

        return combined_results

    async def search(
            self,
            query_embedding: List[float],
            top_k: int,
            namespace: Optional[str] = None,
            filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search for similar vectors and enrich with metadata."""
        # First search for similar vectors
        search_results = await super().search(query_embedding, top_k,
                                              namespace, filter)

        # Get metadata for all results
        vector_ids = [result["id"] for result in search_results]
        metadata_dict = await self.metadata_service.batch_get_metadata(
            vector_ids)

        # Enrich results with metadata
        enriched_results = []
        for result in search_results:
            vector_id = result["id"]
            enriched_result = {
                **result, "metadata": metadata_dict.get(vector_id, {})
            }
            enriched_results.append(enriched_result)

        return enriched_results

    async def delete(self, ids: List[str], namespace: Optional[str] = None):
        """Delete vectors and their metadata."""
        # Delete metadata first
        metadata_results = []
        for idx in ids:
            try:
                await self.metadata_service.delete_metadata(idx)
                metadata_results.append({"status": "success", "id": idx})
            except Exception as e:
                metadata_results.append({
                    "status": "error",
                    "id": idx,
                    "error": str(e)
                })

        # Then delete vectors from Matching Engine
        vector_results = await super().delete(ids, namespace)

        # Combine results
        combined_results = []
        for vec_res, meta_res in zip(vector_results, metadata_results):
            combined = {
                "id": vec_res["id"],
                "vector_status": vec_res["status"],
                "metadata_status": meta_res["status"]
            }
            if vec_res["status"] == "error":
                combined["vector_error"] = vec_res.get("error")
            if meta_res["status"] == "error":
                combined["metadata_error"] = meta_res.get("error")
            combined_results.append(combined)

        return combined_results
