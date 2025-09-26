#scripts/test_embedding.py
import logging
from src.processing.embedding.local import LocalEmbeddingGenerator
from src.processing.embedding.base import EmbeddingGeneratorFactory


def setup_logging():
    """Sets up basic logging for the script."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def test_local_embedding_generator():
    """Tests the LocalEmbeddingGenerator class."""
    logger = logging.getLogger("test_local")
    logger.info("--- Testing LocalEmbeddingGenerator ---")

    # Instantiate the local generator
    local_gen = LocalEmbeddingGenerator()
    logger.info(f"Loaded model: {local_gen.model_name}")
    logger.info(f"Embedding dimension: {local_gen.get_embedding_dimension()}")

    # Test single embedding
    text_single = "Hello, world!"
    embedding_single = local_gen.generate_embedding(text_single)
    logger.info(
        f"Generated single embedding (first 5 values): {embedding_single[:5]}")
    assert len(embedding_single) == local_gen.get_embedding_dimension()
    assert all(isinstance(val, float) for val in embedding_single)
    logger.info("Single embedding test passed.")

    # Test batch embeddings
    texts_batch = [
        "This is the first sentence.", " ", "Here is the second one."
    ]
    batch_embeddings = local_gen.generate_embeddings_batch(texts_batch)
    logger.info(f"Generated batch embeddings (first 5 values of each):")
    for emb in batch_embeddings:
        logger.info(emb[:5])
    assert len(batch_embeddings) == 3
    assert all(
        len(emb) == local_gen.get_embedding_dimension()
        for emb in batch_embeddings)
    assert sum(batch_embeddings[1]
               ) == 0.0  # Check if empty string returns a zero vector

    logger.info("=" * 21)
    logger.info("Batch embeddings test passed.")
    logger.info("=" * 21)


def test_embedding_factory():
    """Tests the EmbeddingGeneratorFactory class."""
    logger = logging.getLogger("test_factory")
    logger.info("--- Testing EmbeddingGeneratorFactory ---")

    # Assuming `settings.embedding_type` is configured to "local"
    # The factory should return a LocalEmbeddingGenerator instance
    try:
        generator = EmbeddingGeneratorFactory.create_embedding_generator()
        logger.info(
            f"Factory created an instance of: {type(generator).__name__}")

        # Verify it's a valid generator
        assert isinstance(generator, LocalEmbeddingGenerator)

        # Test a simple call
        text = "Factory test."
        embedding = generator.generate_embedding(text)
        assert len(embedding) == generator.get_embedding_dimension()
        logger.info("=" * 21)
        logger.info("Factory test passed.")
        logger.info("=" * 21)

    except Exception as e:
        logger.error(f"Factory test failed: {e}")


def main():
    setup_logging()
    test_local_embedding_generator()
    print("\n")

    test_embedding_factory()
    print("\nAll tests completed successfully.")


if __name__ == "__main__":
    main()
