# src/services/vector_db/vertex_ai_matching_engine.py
import logging
import time
from typing import List, Dict, Any, Optional

# Import the necessary high-level objects directly for clarity
from google.cloud import aiplatform
from google.cloud.aiplatform import MatchingEngineIndex
from google.cloud.aiplatform import MatchingEngineIndexEndpoint

# Add this import for the high-level filtering object
from google.cloud.aiplatform.matching_engine.matching_engine_index_endpoint import Namespace as MatchingEngineNamespace

# Import the V1 Index Service Client for management operations and types
from google.cloud.aiplatform_v1.services.index_service import IndexServiceClient

# Import the V1 Index Service Client for management operations and types
from google.cloud.aiplatform_v1.services.index_service import IndexServiceClient
from google.cloud.aiplatform_v1.types import index as gca_index
from google.cloud.aiplatform_v1.types import index_service as gca_index_service
from google.api_core.exceptions import NotFound

from .base import VectorDBService
from src.config import settings

logger_debug = logging.getLogger(__name__)


class VertexAIMatchingEngineService(VectorDBService):
    """Complete implementation of VectorDBService using Vertex AI Matching Engine."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # 1. Initialize client for management operations (upsert/delete/stats)
        self.index_client = self._initialize_index_client()
        # FIX: Use the corrected method to get the resource name
        self.index_name = self._get_index_resource_name()

        # 2. Initialize index and endpoint objects for search operations
        self.index = self._initialize_index()
        self.index_endpoint = self._initialize_index_endpoint()
        self.deployed_index_id = self._get_deployed_index_id()

    def _initialize_index_client(self) -> IndexServiceClient:
        """Initialize the Index Service client with regional endpoint."""
        try:
            return IndexServiceClient(client_options={
                "api_endpoint":
                f"{settings.gcp_region}-aiplatform.googleapis.com"
            })
        except Exception as e:
            self.logger.error(
                f"Failed to initialize IndexServiceClient: {str(e)}")
            raise

    # --- FIX APPLIED HERE ---
    def _get_index_resource_name(self) -> str:
        """Construct the full index resource name for the IndexServiceClient."""
        # Use simple string formatting to construct the resource name,
        # which is the most stable and low-level way.
        return (f"projects/{settings.gcp_project_id}/locations/"
                f"{settings.gcp_region}/indexes/{settings.vertex_ai_index_id}")

    # ------------------------

    def _initialize_index(self) -> MatchingEngineIndex:
        """Initialize the Matching Engine index object."""
        try:
            self.logger.info(
                f"Initializing Matching Engine index: {settings.vertex_ai_index_id}"
            )
            # Use the high-level object imported above
            return MatchingEngineIndex(index_name=settings.vertex_ai_index_id,
                                       project=settings.gcp_project_id,
                                       location=settings.gcp_region)
        except Exception as e:
            self.logger.error(
                f"Failed to initialize Matching Engine index: {str(e)}")
            if settings.vector_db_type != "mock":
                raise

    def _initialize_index_endpoint(self) -> MatchingEngineIndexEndpoint:
        """Initialize the Matching Engine index endpoint object."""
        try:
            self.logger.info(
                f"Initializing Matching Engine endpoint: {settings.vertex_ai_index_endpoint_id}"
            )
            # Use the high-level object imported above
            return MatchingEngineIndexEndpoint(
                index_endpoint_name=settings.vertex_ai_index_endpoint_id,
                project=settings.gcp_project_id,
                location=settings.gcp_region)
        except Exception as e:
            self.logger.error(
                f"Failed to initialize Matching Engine endpoint: {str(e)}")
            if settings.vector_db_type != "mock":
                raise

    def _get_deployed_index_id(self) -> str:
        """Get the deployed index ID from config."""
        return settings.vertex_ai_deployed_index_id

    async def upsert_embeddings(self,
                                vectors: List[List[float]],
                                ids: List[str],
                                metadatas: List[Dict[str, Any]],
                                namespace: Optional[str] = None):
        """Upsert embeddings using IndexServiceClient on the Index resource.
        FIXED to use UpsertDatapointsRequest object.
        """
        if len(vectors) != len(ids) or len(vectors) != len(metadatas):
            raise ValueError(
                "Vectors, IDs, and metadatas must have the same length")

        batch_size = settings.matching_engine_batch_size
        results = []

        for i in range(0, len(vectors), batch_size):
            batch_vectors = vectors[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]

            try:
                # Prepare datapoints with namespace restriction
                # This tells Vertex AI: "For this vector, the filter field named
                # 'namespace_key' has a value of 'public' (or 'user_id')."
                datapoints = []
                for vector, idx in zip(batch_vectors, batch_ids):
                    datapoint = gca_index.IndexDatapoint(
                        datapoint_id=idx,
                        feature_vector=vector,
                        restricts=[
                            # Using a fixed namespace_key and the namespace value as the token
                            gca_index.IndexDatapoint.Restriction(
                                namespace="namespace_key",
                                allow_list=[namespace or "default"])
                        ])
                    datapoints.append(datapoint)

                # --- FIX: Construct the explicit request object ---
                request = gca_index_service.UpsertDatapointsRequest(
                    index=self.index_name,  # The index resource name
                    datapoints=datapoints  # The list of datapoint objects
                )
                # --------------------------------------------------

                # Call upsert on the IndexServiceClient (using the Index resource name)
                self.logger.info(
                    f"Upserting batch of {len(datapoints)} datapoints to index: {self.index_name}"
                )

                # FIX: Pass the single request object
                self.index_client.upsert_datapoints(request=request)

                results.extend([{
                    "status": "success",
                    "id": idx
                } for idx in batch_ids])

                time.sleep(1 / settings.matching_engine_rps_limit)

            except Exception as e:
                self.logger.error(
                    f"Error upserting batch {i}-{i+batch_size}: {str(e)}")
                results.extend([{
                    "status": "error",
                    "id": idx,
                    "error": str(e)
                } for idx in batch_ids])

        return results

    # async def upsert_embeddings(self,
    #                             vectors: List[List[float]],
    #                             ids: List[str],
    #                             metadatas: List[Dict[str, Any]],
    #                             namespace: Optional[str] = None):
    #     """Upsert embeddings using IndexServiceClient on the Index resource."""
    #     if len(vectors) != len(ids) or len(vectors) != len(metadatas):
    #         raise ValueError(
    #             "Vectors, IDs, and metadatas must have the same length")

    #     batch_size = settings.matching_engine_batch_size
    #     results = []

    #     for i in range(0, len(vectors), batch_size):
    #         batch_vectors = vectors[i:i + batch_size]
    #         batch_ids = ids[i:i + batch_size]

    #         try:
    #             # Prepare datapoints with namespace restriction
    #             #This tells Vertex AI: "For this vector, the filter field named
    #             # 'namespace_key' has a value of 'public' (or 'user_id')."
    #             datapoints = []
    #             for vector, idx in zip(batch_vectors, batch_ids):
    #                 datapoint = gca_index.IndexDatapoint(
    #                     datapoint_id=idx,
    #                     feature_vector=vector,
    #                     restricts=[
    #                         # Using a fixed namespace_key and the namespace value as the token
    #                         gca_index.IndexDatapoint.Restriction(
    #                             namespace="namespace_key",
    #                             allow_list=[namespace or "default"])
    #                     ])
    #                 datapoints.append(datapoint)

    #             # Call upsert on the IndexServiceClient (using the Index resource name)
    #             self.logger.info(
    #                 f"Upserting batch of {len(datapoints)} datapoints to index: {self.index_name}"
    #             )

    #             self.index_client.upsert_datapoints(self.index_name,
    #                                                 datapoints)

    #             results.extend([{
    #                 "status": "success",
    #                 "id": idx
    #             } for idx in batch_ids])

    #             time.sleep(1 / settings.matching_engine_rps_limit)

    #         except Exception as e:
    #             self.logger.error(
    #                 f"Error upserting batch {i}-{i+batch_size}: {str(e)}")
    #             results.extend([{
    #                 "status": "error",
    #                 "id": idx,
    #                 "error": str(e)
    #             } for idx in batch_ids])

    #     return results

    async def search(
            self,
            query_embedding: List[float],
            top_k: int,
            namespace: Optional[str] = None,
            filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search with server-side filtering using the high-level SDK Namespace object."""
        try:
            restricts = None
            if namespace:
                # Use the high-level MatchingEngineNamespace object for filtering.
                restricts = [
                    MatchingEngineNamespace(
                        name=
                        "namespace_key",  # Must match the key used during upsert
                        allow_tokens=[namespace])
                ]

            # Call find_neighbors on the Deployed Index Endpoint
            response = self.index_endpoint.find_neighbors(
                deployed_index_id=self.deployed_index_id,
                queries=[query_embedding],
                num_neighbors=top_k,
                # FIX: Use 'filter' keyword, which is required by your current SDK version
                filter=restricts)

            # Format results
            results = []
            for neighbor in response[0]:
                results.append({
                    "id": neighbor.id,
                    "distance": neighbor.distance,
                    "metadata": {
                        "namespace": namespace
                    } if namespace else {}
                })

            return results

        except Exception as e:
            self.logger.error(f"Error searching Matching Engine: {str(e)}")
            raise

    # async def search(
    #         self,
    #         query_embedding: List[float],
    #         top_k: int,
    #         namespace: Optional[str] = None,
    #         filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    #     """Search with server-side filtering using the high-level SDK Namespace object."""
    #     try:
    #         restricts = None
    #         if namespace:
    #             # Use the high-level MatchingEngineNamespace object for filtering.
    #             # 'namespace_key' must match the key used in upsert_embeddings.
    #             restricts = [
    #                 MatchingEngineNamespace(name="namespace_key",
    #                                         allow_tokens=[namespace])
    #             ]
    #         # This ensures that the search query only returns results that match the exact
    #         # key and token established during the upsert process.

    #         # Call find_neighbors on the Deployed Index Endpoint
    #         response = self.index_endpoint.find_neighbors(
    #             deployed_index_id=self.deployed_index_id,
    #             queries=[query_embedding],
    #             num_neighbors=top_k,
    #             restricts=restricts
    #         )  # Use 'restricts' or 'filter' depending on your SDK version. We'll stick to 'restricts' here but use the correct type.

    #         # Format results
    #         results = []
    #         for neighbor in response[0]:
    #             # NOTE: Use neighbor.id and neighbor.distance directly, as confirmed by your test.
    #             # The full document details must be retrieved from a separate store (e.g., Graph DB)
    #             # using this returned 'id'.
    #             results.append({
    #                 "id": neighbor.id,
    #                 "distance": neighbor.distance,
    #                 "metadata": {
    #                     "namespace": namespace
    #                 } if namespace else {}
    #             })

    #         return results

    #     except Exception as e:
    #         self.logger.error(f"Error searching Matching Engine: {str(e)}")
    #         raise

    # async def search(
    #         self,
    #         query_embedding: List[float],
    #         top_k: int,
    #         namespace: Optional[str] = None,
    #         filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    #     """Search with server-side filtering using 'restricts'."""
    #     try:
    #         restricts = None
    #         if namespace:
    #             # Set the restricts for server-side filtering
    #             restricts = [
    #                 gca_index_service.FindNeighborsRequest.Restriction(
    #                     namespace="namespace_key", allow_list=[namespace])
    #             ]

    #         # Call find_neighbors on the Deployed Index Endpoint
    #         response = self.index_endpoint.find_neighbors(
    #             deployed_index_id=self.deployed_index_id,
    #             queries=[query_embedding],
    #             num_neighbors=top_k,
    #             restricts=restricts)

    #         # Format results
    #         results = []
    #         for neighbor in response[0]:
    #             results.append({
    #                 "id": neighbor.datapoint.datapoint_id,
    #                 "distance": neighbor.distance,
    #                 "metadata": {}
    #             })

    #         return results

    #     except Exception as e:
    #         self.logger.error(f"Error searching Matching Engine: {str(e)}")
    #         raise

    async def delete(self, ids: List[str], namespace: Optional[str] = None):
        """Delete vectors using IndexServiceClient on the Index resource."""
        if not ids:
            return

        batch_size = settings.matching_engine_batch_size
        results = []

        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]

            try:
                # Call remove_datapoints on the IndexServiceClient (using the Index resource name)
                self.index_client.remove_datapoints(self.index_name, batch_ids)

                results.extend([{
                    "status": "success",
                    "id": idx
                } for idx in batch_ids])

                time.sleep(1 / settings.matching_engine_rps_limit)

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
            # Get stats by fetching the full Index resource using the client
            index_resource = self.index_client.get_index(name=self.index_name)
            index_stats = index_resource.index_stats

            return {
                "vectors_count":
                index_stats.vectors_count,
                "shards_count":
                index_stats.shards_count,
                "sparse_vectors_count":
                index_stats.sparse_vectors_count if hasattr(
                    index_stats, 'sparse_vectors_count') else 0
            }
        except NotFound:
            self.logger.warning(f"Index resource not found: {self.index_name}")
            return {"error": "Index not found"}
        except Exception as e:
            self.logger.error(f"Error getting index stats: {str(e)}")
            return {}
