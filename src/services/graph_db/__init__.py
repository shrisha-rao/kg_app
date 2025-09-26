# src/services/graph_db/__init__.py
from .base import GraphDBService, Node, Edge, GraphQueryResult
from src.config import settings


def get_graph_db_service() -> GraphDBService:
    """Factory function to get the appropriate GraphDB service."""
    # For now, we only have ArangoDB implementation
    # You can add other implementations in the future
    from .arangodb import ArangoDBService
    return ArangoDBService()
