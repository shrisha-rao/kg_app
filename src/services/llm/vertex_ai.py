# src/services/llm/vertex_ai.py
import logging
from typing import Dict, List, Optional, Any
from google.cloud import aiplatform
# from vertexai.language_models import TextGenerationModel, TextEmbeddingModel

from vertexai.generative_models import GenerativeModel, GenerationConfig
from vertexai.language_models import TextEmbeddingModel  # Keep for embeddings

from .base import LLMService, LLMResponse
from src.config import settings

logger = logging.getLogger(__name__)


class VertexAILLMService(LLMService):
    """Vertex AI implementation of the LLM service"""

    def __init__(self):
        self.project_id = settings.gcp_project_id
        self.region = settings.gcp_region
        self.default_model = settings.vertex_ai_llm_model
        self.embedding_model = settings.vertex_ai_embedding_model

        # Initialize Vertex AI
        aiplatform.init(project=self.project_id, location=self.region)

        # Initialize models
        # self.text_model = TextGenerationModel.from_pretrained(
        #     self.default_model)
        # NEW: Use GenerativeModel for Gemini models
        self.text_model = GenerativeModel(self.default_model)
        self.embedding_model_instance = TextEmbeddingModel.from_pretrained(
            self.embedding_model)

        logger.info(
            f"Initialized Vertex AI LLM service with model: {self.default_model}"
        )

    async def generate_response(self,
                                prompt: str,
                                context: Optional[str] = None,
                                temperature: float = 0.2,
                                max_tokens: int = 1024,
                                **kwargs) -> LLMResponse:
        """Generate a response from Vertex AI LLM"""
        try:
            # Combine context and prompt if context is provided
            full_prompt = f"{context}\n\n{prompt}" if context else prompt

            # --- FIX: Create GenerationConfig for Gemini parameters ---
            config = GenerationConfig(temperature=temperature,
                                      max_output_tokens=max_tokens)
            # --------------------------------------------------------

            response = self.text_model.generate_content(
                full_prompt, generation_config=config, **kwargs)

            # response = self.text_model.predict(...) # OLD/COMMENTED OUT CODE

            return LLMResponse(
                content=response.text,
                model=self.default_model,
                confidence=
                0.8,  # Vertex AI doesn't provide confidence scores directly
                tokens_used=len(
                    response.text.split())  # Approximate token count
            )

        except Exception as e:
            logger.error(f"Error generating response from Vertex AI: {e}")
            raise

    # async def generate_response_OLD(self,
    #                             prompt: str,
    #                             context: Optional[str] = None,
    #                             temperature: float = 0.2,
    #                             max_tokens: int = 1024,
    #                             **kwargs) -> LLMResponse:
    #     """Generate a response from Vertex AI LLM"""
    #     try:
    #         # Combine context and prompt if context is provided
    #         full_prompt = f"{context}\n\n{prompt}" if context else prompt

    #         response = self.text_model.generate_content(
    #             full_prompt,
    #             temperature=temperature,
    #             max_output_tokens=max_tokens,
    #             **kwargs)

    #         # response = self.text_model.predict(full_prompt,
    #         #                                    temperature=temperature,
    #         #                                    max_output_tokens=max_tokens,
    #         #                                    **kwargs)

    #         return LLMResponse(
    #             content=response.text,
    #             model=self.default_model,
    #             confidence=
    #             0.8,  # Vertex AI doesn't provide confidence scores directly
    #             tokens_used=len(
    #                 response.text.split())  # Approximate token count
    #         )

    #     except Exception as e:
    #         logger.error(f"Error generating response from Vertex AI: {e}")
    #         raise

    async def generate_structured_response(self,
                                           prompt: str,
                                           response_format: Dict[str, Any],
                                           context: Optional[str] = None,
                                           temperature: float = 0.1,
                                           max_tokens: int = 1024,
                                           **kwargs) -> Dict[str, Any]:
        """Generate a structured response following a specific format"""
        try:
            # Create a prompt that instructs the model to format the response
            format_instruction = f"Please respond in the following JSON format: {response_format}"
            full_prompt = f"{context}\n\n{format_instruction}\n\n{prompt}" if context else f"{format_instruction}\n\n{prompt}"

            response = self.text_model.predict(full_prompt,
                                               temperature=temperature,
                                               max_output_tokens=max_tokens,
                                               **kwargs)

            # In a real implementation, you would parse the JSON response here
            # For now, return a placeholder
            return {"response": response.text, "format": response_format}

        except Exception as e:
            logger.error(
                f"Error generating structured response from Vertex AI: {e}")
            raise

    async def generate_embeddings(
            self,
            texts: List[str],
            model: Optional[str] = None) -> List[List[float]]:
        """Generate embeddings using Vertex AI Text Embedding Model"""
        try:
            model_to_use = model or self.embedding_model
            embeddings = self.embedding_model_instance.get_embeddings(
                texts, output_dimensionality=settings.embedding_dimension)

            return [embedding.values for embedding in embeddings]

        except Exception as e:
            logger.error(f"Error generating embeddings from Vertex AI: {e}")
            raise

    async def get_available_models(self) -> List[str]:
        """Get list of available Vertex AI models"""
        # This is a simplified implementation
        # In a real implementation, you would query the Vertex AI Model Garden
        return [
            "text-bison@001", "text-bison@002", "chat-bison@001",
            "chat-bison@002", "textembedding-gecko@001",
            "textembedding-gecko@002", "gemini-2.5-flash"
        ]
