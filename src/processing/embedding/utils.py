#src/processing/embedding/utils.py
import logging
from typing import List


def create_zero_vector(dimension: int) -> List[float]:
    """Create a zero vector of the specified dimension."""
    return [0.0] * dimension


def validate_text(text: str) -> bool:
    """Validate if text is suitable for embedding generation."""
    return text is not None and text.strip() != ""


def handle_embedding_error(logger: logging.Logger, dimension: int,
                           error_msg: str) -> List[float]:
    """Handle errors during embedding generation and return a zero vector."""
    logger.error(error_msg)
    return create_zero_vector(dimension)
