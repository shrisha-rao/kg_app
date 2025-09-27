# src/services/file_processing.py
"""
File Processing Service with mock support for development
"""

import uuid
import logging
import os
import re
import hashlib
from typing import Dict, Any, List
from src.config import settings
from src.processing.pdf_extractor import extract_text_from_pdf
from src.processing.ner_extractor import extract_entities_and_relations
from src.services.vector_db import get_vector_db_service
from src.services.graph_db import get_graph_db_service, Node, Edge  # Import Node and Edge
from src.services.storage import get_storage_service
from src.services.llm import get_llm_service
from src.services.compliance import ComplianceFilter
from src.models.paper import PaperCreate, Entity, Relation

logger = logging.getLogger(__name__)


class FileProcessingService:
    """Service for processing uploaded research papers with mock support"""

    def __init__(self):
        self.vector_db = get_vector_db_service()
        self.graph_db = get_graph_db_service()
        self.storage = get_storage_service()
        self.llm = get_llm_service()
        self.compliance = ComplianceFilter()
        self.is_mock_mode = settings.use_mock_services or settings.vector_db_type == "mock"

    async def process_uploaded_file(self,
                                    user_id: str,
                                    file_content: bytes,
                                    filename: str,
                                    metadata: Dict[str, Any] = None,
                                    is_public: bool = False) -> Dict[str, Any]:
        """
        Process an uploaded research paper file with mock support
        """
        if metadata is None:
            metadata = {}

        try:
            if self.graph_db.db is None:
                is_connected = await self.graph_db.connect()
                if not is_connected:
                    raise ConnectionError("Failed to connect to ArangoDB.")

            # Generate unique ID for this document
            doc_id = str(uuid.uuid4())

            # Store raw file (mock or real)
            file_path = f"users/{user_id}/raw/{doc_id}_{filename}"
            if self.is_mock_mode:
                logger.info(f"Mock: Storing file at {file_path}")
            else:
                await self.storage.upload_file(file_content, file_path)

            # Extract text from PDF
            text = extract_text_from_pdf(file_content)
            if self.is_mock_mode:
                logger.info(f"Mock: Extracted {len(text)} characters from PDF")

            # Store extracted text (mock or real)
            text_path = f"users/{user_id}/text/{doc_id}.txt"
            if not self.is_mock_mode:
                await self.storage.upload_file(text.encode('utf-8'), text_path)

            # Extract entities and relations
            entities, relations = await extract_entities_and_relations(text)
            if self.is_mock_mode:
                logger.info(
                    f"Mock: Extracted {len(entities)} entities and {len(relations)} relations"
                )

            # Generate embeddings (mock or real)
            if self.is_mock_mode:
                # Mock embedding vector
                embedding_vector = [0.1] * settings.embedding_dimension
                logger.info(
                    f"Mock: Generated embedding vector of length {len(embedding_vector)}"
                )
            else:
                embeddings = await self.llm.generate_embeddings([text])
                embedding_vector = embeddings[0] if embeddings else []

            # Apply compliance filter
            (public_entities, public_relations, private_entities,
             private_relations) = self.compliance.filter_content(
                 entities, relations, is_public)

            # Prepare metadata for vector DB
            vector_metadata = {
                "user_id": user_id,
                "doc_id": doc_id,
                "filename": filename,
                "is_public": is_public,
                "title": metadata.get("title", filename),
                "authors": metadata.get("authors", []),
                "publication_date": metadata.get("publication_date"),
                "journal": metadata.get("journal"),
                "text_preview": text[:200] + "..." if len(text) > 200 else text
            }

            # Store in vector DB (mock or real)
            if is_public:
                await self.vector_db.upsert_embeddings(
                    vectors=[embedding_vector],
                    ids=[doc_id],
                    metadatas=[{
                        **vector_metadata, "namespace": "public"
                    }],
                    namespace="public")

            # Always add to user's private namespace
            await self.vector_db.upsert_embeddings(
                vectors=[embedding_vector],
                ids=[f"{user_id}_{doc_id}"],
                metadatas=[{
                    **vector_metadata, "namespace": user_id
                }],
                namespace=user_id)

            # Create paper model for database
            paper_data = PaperCreate(
                title=metadata.get("title", filename),
                authors=metadata.get("authors", []),
                publication_date=metadata.get("publication_date"),
                journal_or_conference=metadata.get("journal"),
                doi=metadata.get("doi"),
                abstract=metadata.get(
                    "abstract", text[:500]
                ),  # Use first 500 chars as abstract if not provided
                raw_text_path=text_path,
                pdf_storage_path=file_path,
                file_hash=self._calculate_file_hash(file_content),
                owner_id=user_id)

            # Store in graph DB (both public and private knowledge)
            await self._store_in_graph_db(user_id, doc_id, paper_data,
                                          public_entities, public_relations,
                                          private_entities, private_relations,
                                          is_public)

            logger.info(
                f"Successfully processed file {filename} for user {user_id}")

            return {
                "doc_id": doc_id,
                "filename": filename,
                "text_length": len(text),
                "public_entities_count": len(public_entities),
                "public_relations_count": len(public_relations),
                "private_entities_count": len(private_entities),
                "private_relations_count": len(private_relations),
                "embedding_dimension": len(embedding_vector),
                "is_mock_mode": self.is_mock_mode,
                "status": "completed"
            }

        except Exception as e:
            logger.error(f"Error processing file {filename}: {str(e)}",
                         exc_info=True)
            return {
                "doc_id": doc_id if 'doc_id' in locals() else "unknown",
                "filename": filename,
                "error": str(e),
                "is_mock_mode": self.is_mock_mode,
                "status": "failed"
            }

    def _calculate_file_hash(self, file_content: bytes) -> str:
        """Calculate a hash for the file content"""
        import hashlib
        return hashlib.md5(file_content).hexdigest()

    async def process_uploaded_file_simple(
            self,
            user_id: str,
            file_content: bytes,
            filename: str,
            is_public: bool = False) -> Dict[str, Any]:
        """
        Simplified version for testing without metadata
        """
        return await self.process_uploaded_file(user_id=user_id,
                                                file_content=file_content,
                                                filename=filename,
                                                metadata={"title": filename},
                                                is_public=is_public)

    def _generate_arango_key(self, prefix: str = "") -> str:
        """Generate a guaranteed-safe ArangoDB key using only alphanumeric characters"""
        # Use UUID without any special characters
        safe_key = uuid.uuid4().hex.lower()

        if prefix:
            # Sanitize prefix to be only alphanumeric
            clean_prefix = re.sub(r'[^a-zA-Z0-9]', '', prefix)
            if clean_prefix:
                safe_key = f"{clean_prefix}_{safe_key}"

        return safe_key

    def _build_safe_document_id(self, collection_name: str) -> str:
        """Build a safe document ID with collection name and UUID key"""
        # Sanitize collection name
        clean_collection = re.sub(r'[^a-zA-Z0-9]', '', collection_name)
        if not clean_collection:
            clean_collection = "documents"

        safe_key = self._generate_arango_key()
        return f"{clean_collection}/{safe_key}"

    def _build_safe_edge_id(self, source_key: str, target_key: str,
                            relationship: str) -> str:
        """Build a safe edge ID using hashing"""
        # Extract just the key part (after collection/)
        source_part = source_key.split(
            '/')[-1] if '/' in source_key else source_key
        target_part = target_key.split(
            '/')[-1] if '/' in target_key else target_key

        # Create a unique identifier and hash it
        unique_str = f"{source_part}_{relationship}_{target_part}"
        hash_digest = hashlib.md5(unique_str.encode()).hexdigest()

        return f"edges/{hash_digest}"

    async def _store_in_graph_db(
            self, user_id: str, doc_id: str, paper_data: PaperCreate,
            public_entities: List[Entity], public_relations: List[Relation],
            private_entities: List[Entity], private_relations: List[Relation],
            is_public: bool):
        """Store paper data in the graph database with guaranteed-safe keys"""

        try:
            # Create paper node with safe key
            paper_node_id = self._build_safe_document_id("papers")
            paper_node = Node(
                id=paper_node_id,
                label=paper_data.title[:100],
                properties={
                    "original_doc_id":
                    doc_id,  # Store the original UUID for reference
                    "title":
                    paper_data.title,
                    "authors":
                    paper_data.authors,
                    "publication_date":
                    paper_data.publication_date.isoformat()
                    if paper_data.publication_date else None,
                    "journal":
                    paper_data.journal_or_conference,
                    "doi":
                    paper_data.doi,
                    "abstract":
                    paper_data.abstract,
                    "owner_id":
                    user_id,
                    "is_public":
                    is_public,
                    "is_mock":
                    self.is_mock_mode
                },
                type="paper")

            logger.info(
                f"Attempting to upsert paper node with ID: {paper_node_id}")
            await self.graph_db.upsert_node(paper_node)
            logger.info("Successfully upserted paper node")

            # Track entity mappings for relation creation
            entity_key_map = {}

            # Store public entities
            for i, entity in enumerate(public_entities):
                entity_node_id = self._build_safe_document_id("entities")

                entity_node = Node(id=entity_node_id,
                                   label=entity.text[:100],
                                   properties={
                                       "type": entity.type,
                                       "original_text": entity.text,
                                       "confidence": entity.confidence,
                                       "is_public": True,
                                       "is_mock": self.is_mock_mode,
                                       "entity_index": i
                                   },
                                   type=entity.type)

                logger.info(f"Upserting public entity {i}: {entity_node_id}")
                await self.graph_db.upsert_node(entity_node)
                entity_key_map[(entity.text, False, i)] = entity_node_id

                # Link entity to paper
                edge_id = self._build_safe_edge_id(paper_node_id,
                                                   entity_node_id, "contains")
                relation = Edge(id=edge_id,
                                source_id=paper_node_id,
                                target_id=entity_node_id,
                                label="contains",
                                properties={
                                    "confidence": entity.confidence,
                                    "is_public": True,
                                    "relation_type": "paper_contains_entity"
                                },
                                type="contains")

                logger.info(f"Creating edge from paper to entity: {edge_id}")
                await self.graph_db.upsert_edge(relation)

            # Store private entities
            for i, entity in enumerate(private_entities):
                entity_node_id = self._build_safe_document_id("entities")

                entity_node = Node(
                    id=entity_node_id,
                    label=entity.text[:100],
                    properties={
                        "type": entity.type,
                        "original_text": entity.text,
                        "confidence": entity.confidence,
                        "owner_id": user_id,
                        "is_public": False,
                        "is_mock": self.is_mock_mode,
                        "entity_index":
                        i + len(public_entities)  # Offset index
                    },
                    type=entity.type)

                logger.info(f"Upserting private entity {i}: {entity_node_id}")
                await self.graph_db.upsert_node(entity_node)
                entity_key_map[(entity.text, True, i)] = entity_node_id

                # Link entity to paper
                edge_id = self._build_safe_edge_id(paper_node_id,
                                                   entity_node_id, "contains")
                relation = Edge(id=edge_id,
                                source_id=paper_node_id,
                                target_id=entity_node_id,
                                label="contains",
                                properties={
                                    "confidence": entity.confidence,
                                    "owner_id": user_id,
                                    "is_public": False,
                                    "relation_type": "paper_contains_entity"
                                },
                                type="contains")

                logger.info(
                    f"Creating edge from paper to private entity: {edge_id}")
                await self.graph_db.upsert_edge(relation)

            # Store relations between entities
            all_relations = public_relations + private_relations
            for i, relation in enumerate(all_relations):
                is_private = relation in private_relations

                # Find source and target entities
                source_found = False
                target_found = False
                source_id = None
                target_id = None

                # Look for source entity
                for (text, priv, idx), node_id in entity_key_map.items():
                    if text == relation.source_entity.text and priv == is_private:
                        source_id = node_id
                        source_found = True
                        break

                # Look for target entity
                for (text, priv, idx), node_id in entity_key_map.items():
                    if text == relation.target_entity.text and priv == is_private:
                        target_id = node_id
                        target_found = True
                        break

                if not source_found or not target_found:
                    logger.warning(
                        f"Could not find entity nodes for relation {i}: {relation}"
                    )
                    continue

                # Create relation edge
                edge_id = self._build_safe_edge_id(source_id, target_id,
                                                   relation.relationship)
                relation_edge = Edge(id=edge_id,
                                     source_id=source_id,
                                     target_id=target_id,
                                     label=relation.relationship[:50],
                                     properties={
                                         "confidence": relation.confidence,
                                         "is_public": not is_private,
                                         "original_relationship":
                                         relation.relationship,
                                         "relation_index": i
                                     },
                                     type=relation.relationship[:50])

                logger.info(f"Creating entity relation edge {i}: {edge_id}")
                await self.graph_db.upsert_edge(relation_edge)

            logger.info(
                f"Successfully stored paper {doc_id} with {len(entity_key_map)} entities and {len(all_relations)} relations"
            )

        except Exception as e:
            logger.error(f"Error storing in graph DB: {str(e)}", exc_info=True)
            raise

    def _debug_key_generation(self, original_text: str, generated_key: str):
        """Debug method to log key generation"""
        logger.debug(
            f"Key generation: '{original_text[:50]}...' -> '{generated_key}'")

        # Validate the key
        if not self._validate_arango_key(generated_key.split('/')[-1]):
            logger.warning(f"Generated key may be invalid: {generated_key}")

    def _validate_arango_key(self, key: str) -> bool:
        """Validate if a key part is acceptable for ArangoDB"""
        if not key or len(key) > 254:
            return False

        # ArangoDB key rules: no /, ?, #, [, ], @, !, $, &, ', (, ), *, +, ,, ;, =, spaces, control chars
        if re.search(r'[/?#\[\]@!$&\'()*+,;=\s]', key):
            return False

        # Should not start with underscore (system reserved)
        if key.startswith('_'):
            return False

        return True

    # async def _store_in_graph_db(
    #         self, user_id: str, doc_id: str, paper_data: PaperCreate,
    #         public_entities: List[Entity], public_relations: List[Relation],
    #         private_entities: List[Entity], private_relations: List[Relation],
    #         is_public: bool):
    #     """Store paper data in the graph database with mock support"""

    #     # Create paper node as a Node object
    #     paper_node_id = f"papers/{doc_id}"
    #     paper_node = Node(id=paper_node_id,
    #                       label=paper_data.title,
    #                       properties={
    #                           "title":
    #                           paper_data.title,
    #                           "authors":
    #                           paper_data.authors,
    #                           "publication_date":
    #                           paper_data.publication_date.isoformat()
    #                           if paper_data.publication_date else None,
    #                           "journal":
    #                           paper_data.journal_or_conference,
    #                           "doi":
    #                           paper_data.doi,
    #                           "abstract":
    #                           paper_data.abstract,
    #                           "owner_id":
    #                           user_id,
    #                           "is_public":
    #                           is_public,
    #                           "is_mock":
    #                           self.is_mock_mode
    #                       },
    #                       type="paper")

    #     await self.graph_db.upsert_node(paper_node)

    #     # Store public entities and relations
    #     for entity in public_entities:
    #         #entity_node_id = f"entities/{entity.text.replace(' ', '_').lower()}"
    #         sanitized_text = self._sanitize_key_part(entity.text)
    #         entity_node_id = f"entities/{sanitized_text}"
    #         entity_node = Node(id=entity_node_id,
    #                            label=entity.text,
    #                            properties={
    #                                "type": entity.type,
    #                                "confidence": entity.confidence,
    #                                "is_public": True,
    #                                "is_mock": self.is_mock_mode
    #                            },
    #                            type=entity.type)
    #         await self.graph_db.upsert_node(entity_node)

    #         # Link entity to paper
    #         relation_id = f"relations/{paper_node_id}_{entity_node_id}"
    #         relation = Edge(id=relation_id,
    #                         source_id=paper_node_id,
    #                         target_id=entity_node_id,
    #                         label="contains",
    #                         properties={
    #                             "confidence": entity.confidence,
    #                             "is_public": True
    #                         },
    #                         type="contains")
    #         await self.graph_db.upsert_edge(relation)

    #     # Store private entities and relations
    #     for entity in private_entities:
    #         # entity_node_id = f"users/{user_id}/entities/{entity.text.replace(' ', '_').lower()}"
    #         sanitized_text = self._sanitize_key_part(entity.text)
    #         entity_node_id = f"users/{user_id}/entities/{sanitized_text}"
    #         entity_node = Node(id=entity_node_id,
    #                            label=entity.text,
    #                            properties={
    #                                "type": entity.type,
    #                                "confidence": entity.confidence,
    #                                "owner_id": user_id,
    #                                "is_public": False,
    #                                "is_mock": self.is_mock_mode
    #                            },
    #                            type=entity.type)
    #         await self.graph_db.upsert_node(entity_node)

    #         # Link entity to paper
    #         relation_id = f"users/{user_id}/relations/{paper_node_id}_{entity_node_id}"
    #         relation = Edge(id=relation_id,
    #                         source_id=paper_node_id,
    #                         target_id=entity_node_id,
    #                         label="contains",
    #                         properties={
    #                             "confidence": entity.confidence,
    #                             "owner_id": user_id,
    #                             "is_public": False
    #                         },
    #                         type="contains")
    #         await self.graph_db.upsert_edge(relation)

    #     # Store relations between entities
    #     all_relations = public_relations + private_relations
    #     for relation in all_relations:
    #         is_private_relation = relation in private_relations

    #         # source_entity_text = relation.source_entity.text.replace(
    #         #     ' ', '_').lower()
    #         # target_entity_text = relation.target_entity.text.replace(
    #         #     ' ', '_').lower()
    #         source_entity_text = self._sanitize_key_part(
    #             relation.source_entity.text)
    #         target_entity_text = self._sanitize_key_part(
    #             relation.target_entity.text)

    #         if is_private_relation:
    #             source_id = f"users/{user_id}/entities/{source_entity_text}"
    #             target_id = f"users/{user_id}/entities/{target_entity_text}"
    #         else:
    #             source_id = f"entities/{source_entity_text}"
    #             target_id = f"entities/{target_entity_text}"

    #         relation_id = f"relations/{source_id}_{target_id}_{relation.relationship}"
    #         relation_edge = Edge(id=relation_id,
    #                              source_id=source_id,
    #                              target_id=target_id,
    #                              label=relation.relationship,
    #                              properties={
    #                                  "confidence": relation.confidence,
    #                                  "is_public": not is_private_relation
    #                              },
    #                              type=relation.relationship)
    #         await self.graph_db.upsert_edge(relation_edge)

    #     if self.is_mock_mode:
    #         logger.info(
    #             f"Mock: Stored {len(public_entities)} public and {len(private_entities)} private entities in graph DB"
    #         )
