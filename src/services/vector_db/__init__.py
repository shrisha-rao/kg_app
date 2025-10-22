#src/services/vector_db/__init__.py
# from .base import VectorDBService
# from src.config import settings

# def get_vector_db_service() -> VectorDBService:
#     """Factory function to get the appropriate VectorDB service."""
#     if settings.vector_db_type == "vertex_ai_matching_engine":
#         from .vertex_ai_matching_engine import VertexAIMatchingEngineService
#         return VertexAIMatchingEngineService()
#     elif settings.vector_db_type == "pinecone":
#         from .pinecone_service import PineconeService
#         return PineconeService()
#     else:  # Default to Chroma or other
#         from .chroma_service import ChromaService
#         return ChromaService()

# src/services/vector_db/__init__.py
from .base import VectorDBService
from src.config import settings


def get_vector_db_service() -> VectorDBService:
    """Factory function to get the appropriate VectorDB service."""
    print('x=' * 50)
    print(settings.vector_db_type)
    settings.vector_db_type = "mock"
    print(f"{settings.vertex_ai_llm_model}")
    print(settings.vector_db_type)
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
        from .mock_vector_service import MockVectorService
        return MockVectorService()
    elif settings.vector_db_type == "local":
        from .local_vector_db import LocalVectorDBService
        return LocalVectorDBService()
    else:  # Default to mock for development safety
        from .mock_vector_service import MockVectorService
        return MockVectorService()
