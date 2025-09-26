#src/processing/embedding/vertex_ai.py
import logging
import re
from typing import List, Optional
from google.cloud import aiplatform
from google.cloud.aiplatform_v1.types import content as content_types
from google.cloud.aiplatform_v1.services.prediction_service import PredictionServiceClient
from google.cloud.aiplatform_v1.types import PredictRequest
from .base import EmbeddingGenerator
from src.config import settings


class VertexAIEmbeddingGenerator(EmbeddingGenerator):
    """Cloud-based embedding generator using Vertex AI."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.vertex_ai_embedding_model
        self.logger = logging.getLogger(__name__)
        self.client = self._initialize_client()
        self.embedding_dimension = settings.embedding_dimension
        self.endpoint = self._parse_model_endpoint()

    def _initialize_client(self) -> PredictionServiceClient:
        """Initialize the Vertex AI Prediction Service client."""
        try:
            # Initialize the Vertex AI SDK
            aiplatform.init(
                project=settings.gcp_project_id,
                location=settings.gcp_region,
            )

            # Create a prediction service client
            client_options = {
                "api_endpoint":
                f"{settings.gcp_region}-aiplatform.googleapis.com"
            }
            return PredictionServiceClient(client_options=client_options)
        except Exception as e:
            self.logger.error(
                f"Failed to initialize Vertex AI client: {str(e)}")
            raise

    def _parse_model_endpoint(self) -> str:
        """Parse the model name to extract endpoint information."""
        # Extract project and location from model name if it's a full resource name
        if "/" in self.model_name:
            pattern = r"projects/([^/]+)/locations/([^/]+)/publishers/google/models/([^/]+)"
            match = re.match(pattern, self.model_name)
            if match:
                project = match.group(1)
                location = match.group(2)
                model_short_name = match.group(3)
                return f"projects/{project}/locations/{location}/publishers/google/models/{model_short_name}"

        # Use default project and location from settings
        return f"projects/{settings.gcp_project_id}/locations/{settings.gcp_region}/publishers/google/models/{self.model_name}"

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text string using Vertex AI."""
        if not text or not text.strip():
            return [0.0] * self.embedding_dimension

        try:
            # Prepare the request
            instance = content_types.Content(
                parts=[content_types.Part(text=text)],
                role="user",
            )

            instances = [instance]
            parameters = content_types.PredictionParameters(
                temperature=0.0,
                max_output_tokens=1,  # Not used for embeddings, but required
                top_p=0.0,  # Not used for embeddings, but required
                top_k=1,  # Not used for embeddings, but required
            )

            request = PredictRequest(
                endpoint=self.endpoint,
                instances=instances,
                parameters=parameters,
            )

            # Make the prediction request
            response = self.client.predict(request=request)

            # Extract embeddings from response
            if response.predictions and len(response.predictions) > 0:
                prediction = response.predictions[0]
                if hasattr(prediction, 'struct_value'):
                    # Handle struct value response (textembedding-gecko)
                    if 'embeddings' in prediction.struct_value:
                        embeddings = prediction.struct_value['embeddings']
                        if 'values' in embeddings:
                            return list(embeddings['values'])
                elif isinstance(prediction, list):
                    # Handle list response
                    return prediction

            self.logger.error("Unexpected response format from Vertex AI")
            return [0.0] * self.embedding_dimension

        except Exception as e:
            self.logger.error(
                f"Error generating embedding with Vertex AI: {str(e)}")
            return [0.0] * self.embedding_dimension

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of text strings using Vertex AI."""
        if not texts:
            return []

        # Filter out empty texts
        non_empty_texts = [text for text in texts if text and text.strip()]
        empty_indices = [
            i for i, text in enumerate(texts) if not text or not text.strip()
        ]

        if not non_empty_texts:
            return [[0.0] * self.embedding_dimension for _ in texts]

        try:
            # Prepare instances for all non-empty texts
            instances = []
            for text in non_empty_texts:
                instance = content_types.Content(
                    parts=[content_types.Part(text=text)],
                    role="user",
                )
                instances.append(instance)

            parameters = content_types.PredictionParameters(
                temperature=0.0,
                max_output_tokens=1,
                top_p=0.0,
                top_k=1,
            )

            request = PredictRequest(
                endpoint=self.endpoint,
                instances=instances,
                parameters=parameters,
            )

            # Make the prediction request
            response = self.client.predict(request=request)

            # Process the response
            embeddings = []
            for prediction in response.predictions:
                if hasattr(prediction, 'struct_value'):
                    # Handle struct value response (textembedding-gecko)
                    if 'embeddings' in prediction.struct_value:
                        embedding_values = prediction.struct_value[
                            'embeddings']
                        if 'values' in embedding_values:
                            embeddings.append(list(embedding_values['values']))
                elif isinstance(prediction, list):
                    # Handle list response
                    embeddings.append(prediction)
                else:
                    # Fallback to zero vector
                    embeddings.append([0.0] * self.embedding_dimension)

            # Insert zero vectors for empty texts
            for idx in empty_indices:
                embeddings.insert(idx, [0.0] * self.embedding_dimension)

            return embeddings

        except Exception as e:
            self.logger.error(
                f"Error generating batch embeddings with Vertex AI: {str(e)}")
            return [[0.0] * self.embedding_dimension for _ in texts]

    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embeddings generated by this model."""
        return self.embedding_dimension
