# src/services/compliance.py
import logging
from typing import Tuple, List, Dict, Any
from src.models.paper import Entity, Relation

logger = logging.getLogger(__name__)


class ComplianceFilter:
    """Service for filtering content based on compliance rules"""

    def __init__(self):
        # Define rules for what constitutes public vs private information
        self.public_entity_types = ["concept", "methodology", "organization"]
        self.private_entity_types = ["person", "location"]
        self.sensitive_relations = [
            "authored_by", "located_at", "contact_info"
        ]

    def filter_content(
        self, entities: List[Entity], relations: List[Relation],
        is_public: bool
    ) -> Tuple[List[Entity], List[Relation], List[Entity], List[Relation]]:
        """
        Filter entities and relations based on compliance rules
        
        Returns:
            Tuple of (public_entities, public_relations, private_entities, private_relations)
        """
        if is_public:
            # For public papers, only include public information
            public_entities = [
                entity for entity in entities
                if entity.type in self.public_entity_types
            ]

            public_relations = [
                relation for relation in relations
                if (relation.source_entity.type in self.public_entity_types
                    and relation.target_entity.type in self.public_entity_types
                    and relation.relationship not in self.sensitive_relations)
            ]

            return public_entities, public_relations, [], []
        else:
            # For private papers, separate public and private information
            public_entities = [
                entity for entity in entities
                if entity.type in self.public_entity_types
            ]

            private_entities = [
                entity for entity in entities
                if entity.type in self.private_entity_types
            ]

            public_relations = [
                relation for relation in relations
                if (relation.source_entity.type in self.public_entity_types
                    and relation.target_entity.type in self.public_entity_types
                    and relation.relationship not in self.sensitive_relations)
            ]

            private_relations = [
                relation for relation in relations
                if (relation.source_entity.type in self.private_entity_types
                    or relation.target_entity.type in self.private_entity_types
                    or relation.relationship in self.sensitive_relations)
            ]

            return public_entities, public_relations, private_entities, private_relations

    def is_public_fact(self, entity: Entity, relation: Relation) -> bool:
        """Check if a specific fact (entity-relation pair) can be made public"""
        if entity.type in self.private_entity_types:
            return False

        if relation.relationship in self.sensitive_relations:
            return False

        return True
