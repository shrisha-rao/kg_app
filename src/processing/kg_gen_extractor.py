# src/processing/kg_gen_extractor.py
"""
KG-Gen (Knowledge Graph Generator) integration for entity and relation extraction
https://github.com/stair-lab/kg-gen
"""

import logging
from typing import List, Tuple
from src.models.paper import Entity, Relation
from src.config import settings

logger = logging.getLogger(__name__)


class KGGENExtractor:
    """KG-Gen integration for advanced entity and relation extraction"""

    def __init__(self):
        self.kg_gen = None
        self._initialize_kg_gen()

    def _initialize_kg_gen(self):
        """Initialize the KG-Gen pipeline"""
        try:
            from kg_gen import KGGen

            if settings.use_mock_services or settings.vector_db_type == "mock":
                self.kg_gen = KGGen(
                    model=f"ollama/tinyllama",
                    temperature=0.0,  # Deterministic output
                    api_key=
                    None  # Set if using OpenAI, otherwise use local models
                )

            else:
                # Initialize KG-Gen with configuration
                self.kg_gen = KGGen(
                    model=f"vertex_ai/{settings.vertex_ai_llm_model}",
                    temperature=0.0,  # Deterministic output
                    api_key=
                    None  # Set if using OpenAI, otherwise use local models
                )
            logger.info("KG-Gen initialized successfully")

        except ImportError as e:
            logger.error(f"Failed to import KG-Gen: {e}")
            logger.error("Install with: pip install kg-gen")
            raise
        except Exception as e:
            logger.error(f"Error initializing KG-Gen: {e}")
            raise

    async def extract_entities_and_relations(
            self, text: str) -> Tuple[List[Entity], List[Relation]]:
        """Extract entities and relations using KG-Gen"""
        try:
            if self.kg_gen is None:
                self._initialize_kg_gen()

            # Run KG-Gen extraction
            results = await self._run_kg_gen_extraction(text)

            # Convert KG-Gen results to our models
            entities = self._convert_kg_gen_entities(
                results.get("entities", set()))
            relations = self._convert_kg_gen_relations(
                results.get("relations", set()), entities)

            logger.info(
                f"KG-Gen extracted {len(entities)} entities and {len(relations)} relations"
            )
            return entities, relations

        except Exception as e:
            logger.error(f"Error in KG-Gen extraction: {e}")
            return [], []

    async def _run_kg_gen_extraction(self, text: str) -> dict:
        """Run the actual KG-Gen extraction pipeline"""
        try:
            # For research papers, use appropriate context
            context = "Scientific research paper with entities and relationships"

            # KG-Gen works better with smaller chunks for complex documents
            text_chunks = self._split_text_into_chunks(text)
            all_entities = set()
            all_relations = set()

            for chunk in text_chunks:
                # Extract from each chunk - 'graph' is a custom object, not a dict
                graph = self.kg_gen.generate(input_data=chunk, context=context)
                # Access results using the object's attributes: .entities and .relations
                all_entities.update(getattr(graph, 'entities', set()))
                all_relations.update(getattr(graph, 'relations', set()))

            return {"entities": all_entities, "relations": all_relations}

        except Exception as e:
            logger.error(f"Error running KG-Gen pipeline: {e}")
            return {"entities": set(), "relations": set()}

    # async def _run_kg_gen_extraction(self, text: str) -> dict:
    #     """Run the actual KG-Gen extraction pipeline"""
    #     try:
    #         # For research papers, use appropriate context
    #         context = "Scientific research paper with entities and relationships"

    #         # KG-Gen works better with smaller chunks for complex documents
    #         text_chunks = self._split_text_into_chunks(text)
    #         all_entities = set()
    #         all_relations = set()

    #         for chunk in text_chunks:
    #             # Extract from each chunk
    #             graph = self.kg_gen.generate(input_data=chunk, context=context)
    #             all_entities.update(graph.get("entities", set()))
    #             all_relations.update(graph.get("relations", set()))

    #         return {"entities": all_entities, "relations": all_relations}

    #     except Exception as e:
    #         logger.error(f"Error running KG-Gen pipeline: {e}")
    #         return {"entities": set(), "relations": set()}

    def _split_text_into_chunks(self,
                                text: str,
                                max_chunk_size: int = 1000) -> List[str]:
        """Split text into chunks for KG-Gen processing"""
        # Simple chunking by sentences
        sentences = text.split('. ')
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) < max_chunk_size:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _convert_kg_gen_entities(self, kg_gen_entities: set) -> List[Entity]:
        """Convert KG-Gen entities to our Entity model"""
        entities = []

        for entity_text in kg_gen_entities:
            try:
                entity = Entity(
                    text=entity_text,
                    type=self._infer_entity_type(entity_text),
                    confidence=0.8  # KG-Gen doesn't provide confidence scores
                )
                entities.append(entity)
            except Exception as e:
                logger.warning(f"Failed to convert KG-Gen entity: {e}")
                continue

        return entities

    def _convert_kg_gen_relations(self, kg_gen_relations: set,
                                  entities: List[Entity]) -> List[Relation]:
        """Convert KG-Gen relations to our Relation model"""
        relations = []

        # Create entity lookup by text for matching
        entity_lookup = {entity.text: entity for entity in entities}

        for relation_tuple in kg_gen_relations:
            try:
                if len(relation_tuple) == 3:
                    source_text, relationship, target_text = relation_tuple

                    source_entity = entity_lookup.get(source_text)
                    target_entity = entity_lookup.get(target_text)

                    if source_entity and target_entity:
                        relation = Relation(
                            source_entity=source_entity,
                            target_entity=target_entity,
                            relationship=relationship,
                            confidence=
                            0.8  # KG-Gen doesn't provide confidence scores
                        )
                        relations.append(relation)

            except Exception as e:
                logger.warning(f"Failed to convert KG-Gen relation: {e}")
                continue

        return relations

    def _infer_entity_type(self, entity_text: str) -> str:
        """Infer entity type based on text patterns"""
        # Simple heuristic - you can enhance this
        if any(word in entity_text.lower()
               for word in ['method', 'approach', 'technique', 'algorithm']):
            return "methodology"
        elif any(word in entity_text.lower()
                 for word in ['university', 'institute', 'lab', 'department']):
            return "organization"
        elif any(word in entity_text.lower()
                 for word in ['et al', 'author', 'professor', 'dr.']):
            return "person"
        else:
            return "concept"


# Global instance
kg_gen_extractor = KGGENExtractor()


# Public function to use the extractor
async def extract_entities_and_relations_with_kg_gen(
        text: str) -> Tuple[List[Entity], List[Relation]]:
    """
    Extract entities and relations using KG-Gen
    
    Args:
        text: The text to extract from
        
    Returns:
        Tuple of (entities, relations)
    """
    return await kg_gen_extractor.extract_entities_and_relations(text)
