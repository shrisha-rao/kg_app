# src/services/llm/local_llm.py
import logging
from typing import Dict, List, Optional, Any
from sentence_transformers import SentenceTransformer
from .base import LLMService, LLMResponse

####################################

from .mock_llm import MockLLMService

####################################

logger = logging.getLogger(__name__)


class LocalLLMService(LLMService):
    """Local LLM service using sentence-transformers for embeddings"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        logger.info(f"Initializing Local LLM Service with model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.embedding_dimension = self.model.get_sentence_embedding_dimension(
        )

    async def generate_embeddings(
            self,
            texts: List[str],
            model: Optional[str] = None) -> List[List[float]]:
        """Generate embeddings using local model"""
        logger.info(f"Local: Generating embeddings for {len(texts)} texts")
        embeddings = self.model.encode(texts).tolist()
        logger.info(
            f"Local: Generated {len(embeddings)} embeddings of dimension {len(embeddings[0])}"
        )
        return embeddings

    # For text generation, we can't easily run local LLMs, so use mock responses
    async def generate_response(self,
                                prompt: str,
                                context: Optional[str] = None,
                                temperature: float = 0.2,
                                max_tokens: int = 1024,
                                **kwargs) -> LLMResponse:
        """Generate mock response since we don't have a local text generation model"""
        logger.info(
            f"Local: Generating mock response for prompt: {prompt[:100]}...")

        response_text = f"Local mock response to: {prompt[:50]}... (Embeddings were generated locally)"

        return LLMResponse(
            content=response_text,
            reasoning="This is a mock response from local LLM service",
            confidence=0.8,
            tokens_used=len(response_text.split()),
            model="local-mock",
            metadata={
                "embedding_model":
                self.model.get_sentence_embedding_dimension()
            })

    async def generate_structured_response(self,
                                           prompt: str,
                                           response_format: Dict[str, Any],
                                           context: Optional[str] = None,
                                           temperature: float = 0.1,
                                           max_tokens: int = 1024,
                                           **kwargs) -> Dict[str, Any]:
        """Generate mock structured response"""
        return await MockLLMService().generate_structured_response(
            prompt, response_format, context, temperature, max_tokens,
            **kwargs)

    async def get_available_models(self) -> List[str]:
        """Get available local models"""
        return ["all-MiniLM-L6-v2", "paraphrase-MiniLM-L3-v2"]
