# src/processing/ner_extractor.py
"""The implementation provides:

    Efficient spaCy extraction for when you need fast processing

    Accurate LLM extraction for when you need higher quality results

    Easy switching between methods via environment variable

    Proper error handling and logging

    Compatibility with your existing models and services

    You can switch between methods by setting the NER_EXTRACTION_METHOD environment variable to either "spacy" or "llm".
"""
import logging
import json
from typing import List, Tuple, Dict, Any
from src.models.paper import Entity, Relation
from src.config import settings
from src.services.llm import get_llm_service

# import spacy
# from spacy import displacy
# from spacy.tokens import Span
# from spacy.matcher import Matcher

logger = logging.getLogger(__name__)


class NERExtractor:
    """Base class for NER and relation extraction"""

    def __init__(self):
        self.extraction_method = settings.ner_extraction_method  # "spacy" or "llm"

    async def extract_entities_and_relations(
            self, text: str) -> Tuple[List[Entity], List[Relation]]:
        """Extract entities and relations from text"""
        if self.extraction_method == "spacy":
            return await self._extract_with_spacy(text)
        else:
            return await self._extract_with_llm(text)

    async def _extract_with_spacy(
            self, text: str) -> Tuple[List[Entity], List[Relation]]:
        """Extract entities and relations using spaCy"""
        try:
            # Import spacy (we'll handle the import here to avoid dependency issues if not using spacy)
            import spacy
            from spacy import displacy
            from spacy.tokens import Span
            from spacy.matcher import Matcher

            #pdb.set_trace()  # Set a breakpoint here

            # Load the appropriate spaCy model
            try:
                nlp = spacy.load("en_core_web_sm")
            except OSError:
                # If model is not available, download it
                import subprocess
                subprocess.run(
                    ["python", "-m", "spacy", "download", "en_core_web_sm"])
                nlp = spacy.load("en_core_web_sm")

            # Process the text
            doc = nlp(text)

            entities = []
            relations = []

            # Extract entities
            for ent in doc.ents:
                # Map spaCy entity types to our types
                entity_type = self._map_spacy_entity_type(ent.label_)
                if entity_type:
                    entities.append(
                        Entity(
                            text=ent.text,
                            type=entity_type,
                            confidence=
                            1.0  # spaCy doesn't provide confidence scores
                        ))

            # Extract relations using pattern matching
            relations = self._extract_relations_with_patterns(doc)

            logger.info(
                f"Extracted {len(entities)} entities and {len(relations)} relations with spaCy"
            )
            return entities, relations

        except ImportError:
            logger.error(
                "spaCy is not installed. Please install it with: pip install spacy"
            )
            return [], []
        except Exception as e:
            logger.error(f"Error in spaCy extraction: {e}")
            return [], []

    def _map_spacy_entity_type(self, spacy_type: str) -> str:
        """Map spaCy entity types to our entity types"""
        mapping = {
            "PERSON": "person",
            "ORG": "organization",
            "GPE": "location",
            "LOC": "location",
            "FAC": "location",
            "PRODUCT": "concept",
            "EVENT": "concept",
            "WORK_OF_ART": "concept",
            "LAW": "concept",
            "LANGUAGE": "concept",
            "DATE": None,  # We don't want dates
            "TIME": None,  # We don't want times
            "PERCENT": None,  # We don't want percentages
            "MONEY": None,  # We don't want monetary values
            "QUANTITY": None,  # We don't want quantities
            "ORDINAL": None,  # We don't want ordinals
            "CARDINAL": None,  # We don't want cardinals
        }
        return mapping.get(spacy_type, "concept")  # Default to concept

    def _extract_relations_with_patterns(self, doc) -> List[Relation]:
        """Extract relations using pattern matching"""
        relations = []

        # Define patterns for common relations in research papers
        patterns = [
            # Pattern for "method X is used for Y"
            [{
                "POS": "NOUN",
                "OP": "*"
            }, {
                "POS": "VERB",
                "OP": "*"
            }, {
                "POS": "ADP",
                "OP": "*"
            }, {
                "POS": "NOUN",
                "OP": "+"
            }],
            # Pattern for "X et al. proposed Y"
            [{
                "ENT_TYPE": "PERSON",
                "OP": "+"
            }, {
                "LOWER": "et",
                "OP": "*"
            }, {
                "LOWER": "al",
                "OP": "*"
            }, {
                "LOWER": ".",
                "OP": "*"
            }, {
                "POS": "VERB",
                "OP": "+"
            }, {
                "POS": "NOUN",
                "OP": "+"
            }],
            # Pattern for "X is based on Y"
            [{
                "POS": "NOUN",
                "OP": "+"
            }, {
                "LOWER": "is"
            }, {
                "LOWER": "based"
            }, {
                "LOWER": "on"
            }, {
                "POS": "NOUN",
                "OP": "+"
            }]
        ]

        # Create a matcher
        # nlp = doc._.__class__  # Get the nlp object from the doc
        #nlp = doc.__class__
        matcher = Matcher(doc.vocab)

        for i, pattern in enumerate(patterns):
            matcher.add(f"RELATION_{i}", [pattern])

        matches = matcher(doc)

        for match_id, start, end in matches:
            span = doc[start:end]
            # This is a simplified implementation
            # In a real implementation, you would parse the span to extract specific entities and relations

            # For now, we'll just create a generic relation
            if len(span.ents) >= 2:
                source = span.ents[0]
                target = span.ents[1]

                source_type = self._map_spacy_entity_type(source.label_)
                target_type = self._map_spacy_entity_type(target.label_)

                if source_type and target_type:
                    relations.append(
                        Relation(
                            source_entity=Entity(text=source.text,
                                                 type=source_type,
                                                 confidence=1.0),
                            target_entity=Entity(text=target.text,
                                                 type=target_type,
                                                 confidence=1.0),
                            relationship="related_to",
                            confidence=
                            0.7  # Default confidence for pattern-based relations
                        ))

        return relations

    async def _extract_with_llm(
            self, text: str) -> Tuple[List[Entity], List[Relation]]:
        """Extract entities and relations using LLM"""
        try:
            llm_service = get_llm_service()

            # Create a prompt for the LLM to extract entities and relations
            prompt = f"""
            Extract named entities and their relationships from the following research paper text.
            
            Return the results in JSON format with two arrays: "entities" and "relations".
            
            For entities, include:
            - text: the entity text
            - type: one of ["person", "organization", "location", "concept", "methodology"]
            - confidence: a confidence score between 0 and 1
            
            For relations, include:
            - source: the source entity text
            - target: the target entity text
            - relationship: the type of relationship
            - confidence: a confidence score between 0 and 1
            
            Text to analyze:
            {text[:4000]}  # Limit text length to avoid token limits
            
            JSON Response:
            """

            # Get response from LLM
            response = await llm_service.generate_response(prompt,
                                                           temperature=0.1,
                                                           max_tokens=2000)

            # Parse the JSON response
            try:
                # Extract JSON from the response (LLM might add some text before/after JSON)
                json_start = response.content.find('{')
                json_end = response.content.rfind('}') + 1
                json_str = response.content[json_start:json_end]

                data = json.loads(json_str)

                # Convert to our models
                entities = []
                for entity_data in data.get("entities", []):
                    entities.append(
                        Entity(text=entity_data.get("text", ""),
                               type=entity_data.get("type", "concept"),
                               confidence=entity_data.get("confidence", 0.5)))

                relations = []
                for relation_data in data.get("relations", []):
                    # Find the source and target entities
                    source_entity = next(
                        (e for e in entities
                         if e.text == relation_data.get("source", "")), None)
                    target_entity = next(
                        (e for e in entities
                         if e.text == relation_data.get("target", "")), None)

                    if source_entity and target_entity:
                        relations.append(
                            Relation(source_entity=source_entity,
                                     target_entity=target_entity,
                                     relationship=relation_data.get(
                                         "relationship", "related_to"),
                                     confidence=relation_data.get(
                                         "confidence", 0.5)))

                logger.info(
                    f"Extracted {len(entities)} entities and {len(relations)} relations with LLM"
                )
                return entities, relations

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.error(f"LLM response: {response.content}")
                return [], []

        except Exception as e:
            logger.error(f"Error in LLM extraction: {e}")
            return [], []


# Global instance
ner_extractor = NERExtractor()


# Public function to use the extractor
async def extract_entities_and_relations(
        text: str) -> Tuple[List[Entity], List[Relation]]:
    """
    Extract entities and relations from text
    
    Args:
        text: The text to extract from
        
    Returns:
        Tuple of (entities, relations)
    """
    return await ner_extractor.extract_entities_and_relations(text)
