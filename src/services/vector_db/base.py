#src/services/vector_db/base.py
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class VectorDBService(ABC):

    @abstractmethod
    async def upsert_embeddings(self,
                                vectors: List[List[float]],
                                ids: List[str],
                                metadatas: List[Dict[str, Any]],
                                namespace: Optional[str] = None):
        """Upsert embeddings into the vector database"""
        pass

    @abstractmethod
    async def search(
            self,
            query_embedding: List[float],
            top_k: int,
            namespace: Optional[str] = None,
            filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search for similar vectors"""
        pass

    @abstractmethod
    async def delete(self, ids: List[str], namespace: Optional[str] = None):
        """Delete vectors by IDs"""
        pass
