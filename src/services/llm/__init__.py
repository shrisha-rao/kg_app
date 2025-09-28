# # src/services/llm/__init__.py
# from .base import LLMService, LLMResponse
# from src.config import settings

# def get_llm_service() -> LLMService:
#     """Factory function to get the appropriate LLM service."""
#     # For now, we only have Vertex AI implementation
#     # You can add other implementations in the future (e.g., OpenAI, Anthropic, etc.)
#     from .vertex_ai import VertexAILLMService
#     return VertexAILLMService()

# src/services/llm/__init__.py (updated)
import os
import logging
from src.config import settings

logging.basicConfig(level=logging.DEBUG)
# or for uvicorn:
logging.getLogger("uvicorn").setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)


def get_llm_service():
    """Return appropriate LLM service based on environment and configuration"""

    # Use mock service if we're using emulators
    if settings.use_mock_services or settings.vector_db_type == "mock":
        from .mock_llm import MockLLMService
        logger.info("Using Mock LLM Service (development mode)")
        return MockLLMService()

    # Use local embeddings if configured
    if settings.embedding_type == "local":
        from .local_llm import LocalLLMService
        logger.info(
            f"Using Local LLM Service with model: {settings.local_embedding_model}"
        )
        return LocalLLMService(model_name=settings.local_embedding_model)

    # Otherwise use the real Vertex AI service
    try:
        from .vertex_ai import VertexAILLMService
        logger.info("Using Vertex AI LLM Service (production mode)")
        return VertexAILLMService()
    except ImportError as e:
        logger.warning(
            f"Vertex AI LLM service not available, falling back to mock: {e}")
        from .mock_llm import MockLLMService
        return MockLLMService()
