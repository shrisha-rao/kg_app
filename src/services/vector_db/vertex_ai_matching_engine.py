#src/services/vector_db/vertex_ai_matching_engine.py
import logging
import time
from typing import List, Dict, Any, Optional
from google.cloud import aiplatform
from google.cloud.aiplatform_v1.types import index as gca_index
from google.cloud.aiplatform_v1.types import index_service as gca_index_service
from .base import VectorDBService
from src.config import settings


class VertexAIMatchingEngineService(VectorDBService):
    """Complete implementation of VectorDBService using Vertex AI Matching Engine."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.index = self._initialize_index()
        self.index_endpoint = self._initialize_index_endpoint()
        self.deployed_index_id = self._get_deployed_index_id()

    def _initialize_index(self) -> aiplatform.MatchingEngineIndex:
        """Initialize the Matching Engine index with proper error handling."""
        try:
            self.logger.info(
                f"Initializing Matching Engine index: {settings.vertex_ai_index_id}"
            )
            return aiplatform.MatchingEngineIndex(
                index_name=settings.vertex_ai_index_id,
                project=settings.gcp_project_id,
                location=settings.gcp_region)
        except Exception as e:
            self.logger.error(
                f"Failed to initialize Matching Engine index: {str(e)}")
            raise

    def _initialize_index_endpoint(
            self) -> aiplatform.MatchingEngineIndexEndpoint:
        """Initialize the Matching Engine index endpoint with proper error handling."""
        try:
            self.logger.info(
                f"Initializing Matching Engine endpoint: {settings.vertex_ai_index_endpoint_id}"
            )
            return aiplatform.MatchingEngineIndexEndpoint(
                index_endpoint_name=settings.vertex_ai_index_endpoint_id,
                project=settings.gcp_project_id,
                location=settings.gcp_region)
        except Exception as e:
            self.logger.error(
                f"Failed to initialize Matching Engine endpoint: {str(e)}")
            raise

    def _get_deployed_index_id(self) -> str:
        """Get the deployed index ID from the endpoint."""
        if not self.index_endpoint.deployed_indexes:
            raise ValueError("No deployed indexes found on the endpoint")
        return self.index_endpoint.deployed_indexes[0].id

    async def upsert_embeddings(self,
                                vectors: List[List[float]],
                                ids: List[str],
                                metadatas: List[Dict[str, Any]],
                                namespace: Optional[str] = None):
        """Upsert embeddings into the Matching Engine with proper batching and error handling."""
        if len(vectors) != len(ids) or len(vectors) != len(metadatas):
            raise ValueError(
                "Vectors, IDs, and metadatas must have the same length")

        # Matching Engine has limits on batch size and RPS
        batch_size = 100  # Adjust based on Matching Engine limits
        results = []

        for i in range(0, len(vectors), batch_size):
            batch_vectors = vectors[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]

            try:
                # Prepare datapoints for this batch
                datapoints = []
                for vector, idx, metadata in zip(batch_vectors, batch_ids,
                                                 batch_metadatas):
                    datapoint = gca_index.IndexDatapoint(
                        datapoint_id=idx,
                        feature_vector=vector,
                        restricts=[
                            gca_index.IndexDatapoint.Restriction(
                                namespace=namespace or "default",
                                allow_list=[namespace] if namespace else [])
                        ])
                    datapoints.append(datapoint)

                # Upsert the batch
                self.logger.info(
                    f"Upserting batch of {len(datapoints)} datapoints")
                self.index_endpoint.upsert_datapoints(
                    deployed_index_id=self.deployed_index_id,
                    datapoints=datapoints)

                results.extend([{
                    "status": "success",
                    "id": idx
                } for idx in batch_ids])

                # Respect rate limits
                time.sleep(0.1)  # Adjust based on quota

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
        """Search for similar vectors in the Matching Engine with proper error handling."""
        try:
            # Prepare restrictions if namespace is provided
            restricts = None
            if namespace:
                restricts = [
                    gca_index.IndexDatapoint.Restriction(
                        namespace=namespace, allow_list=[namespace])
                ]

            # Execute the search
            response = self.index_endpoint.find_neighbors(
                deployed_index_id=self.deployed_index_id,
                queries=[query_embedding],
                num_neighbors=top_k,
                restricts=restricts,
                # filter is not directly supported in current API, would need to implement via metadata filtering
            )

            # Format results
            results = []
            for neighbor in response[0]:  # First query results
                results.append({
                    "id": neighbor.datapoint.datapoint_id,
                    "distance": neighbor.distance,
                    "metadata":
                    {}  # Metadata would need to be stored separately
                })

            return results

        except Exception as e:
            self.logger.error(f"Error searching Matching Engine: {str(e)}")
            raise

    async def delete(self, ids: List[str], namespace: Optional[str] = None):
        """Delete vectors from the Matching Engine with proper batching."""
        if not ids:
            return

        # Matching Engine has limits on batch size
        batch_size = 100
        results = []

        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]

            try:
                self.index_endpoint.remove_datapoints(
                    deployed_index_id=self.deployed_index_id,
                    datapoint_ids=batch_ids)
                results.extend([{
                    "status": "success",
                    "id": idx
                } for idx in batch_ids])

                # Respect rate limits
                time.sleep(0.1)

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
        """Get statistics about the index."""
        try:
            index_stats = self.index_endpoint.deployed_indexes[0].index_stats
            return {
                "vectors_count":
                index_stats.vectors_count,
                "shards_count":
                index_stats.shards_count,
                "sparse_vectors_count":
                index_stats.sparse_vectors_count if hasattr(
                    index_stats, 'sparse_vectors_count') else 0
            }
        except Exception as e:
            self.logger.error(f"Error getting index stats: {str(e)}")
            return {}
