# src/config.py
import os
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # GCP Configuration
    gcp_project_id: str = Field("dev-project", env="GCP_PROJECT_ID")
    gcp_region: str = Field("us-central1", env="GCP_REGION")

    # Storage
    gcs_bucket_name: str = Field("dev-bucket", env="GCS_BUCKET_NAME")

    # Vector DB
    vector_db_type: str = Field(
        "mock", env="VECTOR_DB_TYPE")  # Default to mock for development

    # Vertex AI Matching Engine Configuration (optional for development)
    vertex_ai_index_id: str = Field("", env="VERTEX_AI_INDEX_ID")
    vertex_ai_index_endpoint_id: str = Field("",
                                             env="VERTEX_AI_INDEX_ENDPOINT_ID")
    vertex_ai_index_region: str = Field("us-central1",
                                        env="VERTEX_AI_INDEX_REGION")

    vertex_ai_deployed_index_id: str = Field(
        default="research_deployed_index_v1",
        env="VERTEX_AI_DEPLOYED_INDEX_ID")

    matching_engine_batch_size: int = Field(100,
                                            env="MATCHING_ENGINE_BATCH_SIZE")
    matching_engine_rps_limit: int = Field(10, env="MATCHING_ENGINE_RPS_LIMIT")

    # Graph DB
    arangodb_host: str = Field("arangodb", env="ARANGODB_HOST")
    arangodb_username: str = Field("root", env="ARANGODB_USERNAME")
    arangodb_password: str = Field("my-secret-password",
                                   env="ARANGODB_PASSWORD")
    arangodb_database: str = Field("research", env="ARANGODB_DATABASE")
    arangodb_test_db: str = Field("test", env="ARANGODB_TEST_DB")

    # LLM
    #"text-bison@001",
    vertex_ai_llm_model: str = Field("gemini-2.5-flash",
                                     env="VERTEX_AI_LLM_MODEL")

    # Redis
    redis_host: str = Field("redis", env="REDIS_HOST")
    redis_port: int = Field(6379, env="REDIS_PORT")

    # Authentication (simplified for example)
    secret_key: str = Field("dev-secret-key", env="SECRET_KEY")

    # Embedding Configuration
    embedding_type: str = Field("vertex_ai",
                                env="EMBEDDING_TYPE")  # "local" or "vertex_ai"
    local_embedding_model: str = Field(
        "all-mpnet-base-v2", env="LOCAL_EMBEDDING_MODEL")  #  all-MiniLM-L6-v2
    #"textembedding-gecko@002",
    vertex_ai_embedding_model: str = Field("gemini-embedding-001",
                                           env="VERTEX_AI_EMBEDDING_MODEL")
    embedding_dimension: int = Field(3072, env="EMBEDDING_DIMENSION")
    # 384 for all-MiniLM-L6-v2 # 768 forall-mpnet-base-v2
    # 3072 for gemini-embedding-001

    # Other Vector DB options
    pinecone_api_key: str = Field("", env="PINECONE_API_KEY")
    pinecone_environment: str = Field("", env="PINECONE_ENVIRONMENT")
    pinecone_index_name: str = Field("", env="PINECONE_INDEX_NAME")

    # NER Extraction Configuration
    ner_extraction_method: str = Field(
        "kg_gen", env="NER_EXTRACTION_METHOD")  # "spacy", "llm", or "kg_gen"

    # PDF Extraction Configuration
    pdf_use_ocr: bool = Field(
        False, env="PDF_USE_OCR")  # Whether to use OCR for scanned PDFs
    pdf_ocr_language: str = Field("eng",
                                  env="PDF_OCR_LANGUAGE")  # Language for OCR

    # Emulator and Development Settings
    firestore_emulator_host: Optional[str] = Field(
        None, env="FIRESTORE_EMULATOR_HOST")
    use_mock_services: bool = Field(True, env="USE_MOCK_SERVICES")

    class Config:
        # env_file = ".env.local"
        extra = "ignore"  # This allows extra environment variables without throwing errors


settings = Settings()

logger.info(f"Loading ARANGODB_HOST: {os.getenv('ARANGODB_HOST')}")
logger.info(f"Loading USE_MOCK_SERVICES: {os.getenv('USE_MOCK_SERVICES')}")
