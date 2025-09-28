# src/services/llm/mock_llm.py
import logging
import random
from typing import Dict, List, Optional, Any
from .base import LLMService, LLMResponse

logger = logging.getLogger(__name__)


class MockLLMService(LLMService):
    """Mock LLM service for development/testing"""

    def __init__(self):
        logger.info("Initializing Mock LLM Service for development")
        self.embedding_dimension = 384  # Match your local embedding model

    async def generate_response(self,
                                prompt: str,
                                context: Optional[str] = None,
                                temperature: float = 0.2,
                                max_tokens: int = 1024,
                                **kwargs) -> LLMResponse:
        """Mock LLM response generation"""
        logger.info(
            f"Mock: Generating response for prompt: {prompt[:100]}... ")

        # Generate a mock response
        mock_response = f"Mock response to: {prompt[:50]}... This is a simulated LLM response for development purposes."

        return LLMResponse(content=mock_response,
                           reasoning="This is mock reasoning for development",
                           confidence=0.9,
                           tokens_used=len(mock_response.split()),
                           model="mock-llm",
                           metadata={"is_mock": True})

    async def generate_structured_response(self,
                                           prompt: str,
                                           response_format: Dict[str, Any],
                                           context: Optional[str] = None,
                                           temperature: float = 0.1,
                                           max_tokens: int = 1024,
                                           **kwargs) -> Dict[str, Any]:
        """Mock structured response generation"""
        logger.info(
            f"Mock: Generating structured response for prompt: {prompt[:100]}..."
        )

        # Generate a mock structured response based on the format
        mock_response = {}
        for key, value_type in response_format.items():
            if key == "suggested_follow_up_questions" or key == "questions":
                mock_response[key] = [
                    "What else would you like to explore?",
                    "Any clarifying details needed?",
                    "Related experiments to consider?"
                ]
            elif value_type == "string":
                mock_response[key] = f"mock_{key}_value"
            elif value_type == "number":
                mock_response[key] = 42.0
            elif value_type == "boolean":
                mock_response[key] = True
            elif value_type == "array":
                mock_response[key] = ["mock_item_1", "mock_item_2"]
            else:
                mock_response[key] = f"mock_{key}"

        mock_response["is_mock"] = True
        logger.info(f"mock_response = {mock_response}")
        return mock_response

    async def generate_embeddings(
            self,
            texts: List[str],
            model: Optional[str] = None) -> List[List[float]]:
        """Mock embedding generation"""
        logger.info(f"Mock: Generating embeddings for {len(texts)} texts")

        embeddings = []
        for text in texts:
            # Generate deterministic mock embeddings based on text content
            # This ensures same text always gets same embedding
            seed = hash(text) % 10000
            random.seed(seed)
            embedding = [
                random.uniform(-1, 1) for _ in range(self.embedding_dimension)
            ]
            embeddings.append(embedding)

        logger.info(
            f"Mock: Generated {len(embeddings)} embeddings of dimension {self.embedding_dimension}"
        )
        return embeddings

    async def get_available_models(self) -> List[str]:
        """Mock model list"""
        return ["mock-text-model", "mock-embedding-model"]
