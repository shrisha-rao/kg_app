#src/services/vector_db/vertex_ai_engine.py
from google.cloud import aiplatform
from typing import List, Optional, Dict, Any
from .base import VectorDBService
from src.config import settings


class VertexAIVectorDBService(VectorDBService):

    def __init__(self):
        self.index = aiplatform.MatchingEngineIndex(
            index_name=settings.vertex_ai_index_id,
            project=settings.gcp_project_id,
            location=settings.gcp_region)
        self.index_endpoint = aiplatform.MatchingEngineIndexEndpoint(
            index_endpoint_name=settings.vertex_ai_index_endpoint_id,
            project=settings.gcp_project_id,
            location=settings.gcp_region)

    async def upsert_embeddings(self, vectors, ids, metadatas, namespace=None):
        # Convert to Vertex AI format
        deployed_index_id = self.index_endpoint.deployed_indexes[0].id
        self.index_endpoint.upsert_embeddings(
            deployed_index_id=deployed_index_id,
            embeddings=vectors,
            ids=ids,
            metadatas=metadatas,
            namespace=namespace)

    async def search(self,
                     query_embedding,
                     top_k,
                     namespace=None,
                     filter=None):
        deployed_index_id = self.index_endpoint.deployed_indexes[0].id
        response = self.index_endpoint.find_neighbors(
            deployed_index_id=deployed_index_id,
            queries=[query_embedding],
            num_neighbors=top_k,
            filter=filter,
            namespace=namespace)
        return response[0]  # Return results for the first query
