# src/services/llm/base.py
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from pydantic import BaseModel


class LLMResponse(BaseModel):
    """Standardized response from LLM service"""
    content: str
    reasoning: Optional[str] = None
    confidence: float = 0.0
    tokens_used: Optional[int] = None
    model: str
    metadata: Dict[str, Any] = {}


class LLMService(ABC):
    """Abstract base class for LLM services"""

    @abstractmethod
    async def generate_response(self,
                                prompt: str,
                                context: Optional[str] = None,
                                temperature: float = 0.2,
                                max_tokens: int = 1024,
                                **kwargs) -> LLMResponse:
        """Generate a response from the LLM given a prompt and optional context"""
        pass

    @abstractmethod
    async def generate_structured_response(self,
                                           prompt: str,
                                           response_format: Dict[str, Any],
                                           context: Optional[str] = None,
                                           temperature: float = 0.1,
                                           max_tokens: int = 1024,
                                           **kwargs) -> Dict[str, Any]:
        """Generate a structured response following a specific format"""
        pass

    @abstractmethod
    async def generate_embeddings(
            self,
            texts: List[str],
            model: Optional[str] = None) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        pass

    @abstractmethod
    async def get_available_models(self) -> List[str]:
        """Get list of available models"""
        pass
