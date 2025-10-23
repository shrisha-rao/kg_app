# src/services/vector_db/__init__.py
from .base import VectorDBService
from src.config import settings


def get_vector_db_service() -> VectorDBService:
    """Factory function to get the appropriate VectorDB service."""
    print('x=' * 50)
    print(settings.vector_db_type)
    # settings.vector_db_type = "local"
    print(
        f"inside vectordb __init__ {settings.vertex_ai_llm_model} {settings.vector_db_type}"
    )
    print(settings.vector_db_type)

    # Add explicit comparison debugging
    print(f"🔍 Comparing to 'local': {settings.vector_db_type == 'local'}")
    print(f"🔍 Comparing to 'mock': {settings.vector_db_type == 'mock'}")

    print('=x' * 50)
    if settings.vector_db_type == "vertex_ai_matching_engine":
        from .vertex_ai_matching_engine import VertexAIMatchingEngineService
        return VertexAIMatchingEngineService()
    elif settings.vector_db_type == "pinecone":
        from .pinecone_service import PineconeService
        return PineconeService()
    elif settings.vector_db_type == "chroma":
        from .chroma_service import ChromaService
        return ChromaService()
    elif settings.vector_db_type == "mock":
        print("🔧 Loading MockVectorService")
        from .mock_vector_service import MockVectorService
        return MockVectorService()
    elif settings.vector_db_type == "local":
        print("🔧 Loading LocalVectorDBService")
        from .local_vector_db import LocalVectorDBService
        return LocalVectorDBService()
    else:  # Default to mock for development safety
        print("🔧 Loading MockVectorService (default fallback)")
        from .mock_vector_service import MockVectorService
        return MockVectorService()
