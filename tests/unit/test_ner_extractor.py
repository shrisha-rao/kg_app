# tests/unit/test_ner_extractor.py
import sys
import os
import logging
import asyncio
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.processing.ner_extractor import extract_entities_and_relations, NERExtractor

# Set up basic logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


async def test_ner_extractor():
    """Test the NER extractor with sample research text"""

    # Sample research paper text for testing
    sample_text = """
    In their 2020 study, Dr. Jane Smith from Stanford University proposed a novel machine learning framework 
    called NeuroLearn for analyzing neurological data. The research was conducted in collaboration with 
    researchers at MIT and Harvard Medical School. The methodology combines convolutional neural networks 
    with attention mechanisms, achieving 95% accuracy on the Alzheimer's Disease dataset. 
    This approach significantly outperforms traditional methods like SVM and random forests.
    """

    print("Testing NER Extractor...")
    print("=" * 50)

    # Test spaCy extraction
    print("\n🧪 Testing spaCy NER Extraction")
    extractor = NERExtractor()
    extractor.extraction_method = "spacy"

    try:
        entities, relations = await extractor.extract_entities_and_relations(
            sample_text)
        print(f"✅ spaCy extraction successful")
        print(f"👤 Entities found: {len(entities)}")
        for entity in entities:
            print(
                f"   - {entity.text} ({entity.type}, confidence: {entity.confidence})"
            )

        print(f"🔗 Relations found: {len(relations)}")
        for relation in relations[:3]:  # Show first 3 relations
            print(
                f"   - {relation.source_entity.text} → {relation.target_entity.text} ({relation.relationship})"
            )

    except Exception as e:
        print(f"❌ spaCy extraction failed: {e}")

    # Test LLM extraction (if configured)
    print("\n🧪 Testing LLM NER Extraction")
    extractor.extraction_method = "llm"

    try:
        entities, relations = await extractor.extract_entities_and_relations(
            sample_text)
        print(f"✅ LLM extraction successful")
        print(f"👤 Entities found: {len(entities)}")
        for entity in entities:
            print(
                f"   - {entity.text} ({entity.type}, confidence: {entity.confidence})"
            )

        print(f"🔗 Relations found: {len(relations)}")
        for relation in relations[:3]:
            print(
                f"   - {relation.source_entity.text} → {relation.target_entity.text} ({relation.relationship})"
            )

    except Exception as e:
        print(f"❌ LLM extraction failed: {e}")
        print("💡 Note: LLM extraction requires Vertex AI configuration")


def test_entity_mapping():
    """Test spaCy entity type mapping"""
    print("\n🧪 Testing Entity Type Mapping")

    extractor = NERExtractor()

    # Test spaCy entity type mapping
    test_cases = [
        ("PERSON", "person"),
        ("ORG", "organization"),
        ("GPE", "location"),
        ("PRODUCT", "concept"),
        ("UNKNOWN_TYPE", "concept")  # Default mapping
    ]

    for spacy_type, expected_type in test_cases:
        mapped_type = extractor._map_spacy_entity_type(spacy_type)
        status = "✅" if mapped_type == expected_type else "❌"
        print(
            f"{status} {spacy_type} → {mapped_type} (expected: {expected_type})"
        )


async def main():
    await test_ner_extractor()
    test_entity_mapping()


if __name__ == "__main__":
    asyncio.run(main())

# # tests/unit/test_ner_extractor.py

# """The script tests both extraction methods and entity type mapping.
# """
# import sys
# import os
# import logging
# from pathlib import Path

# # Add the src directory to the Python path
# sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# from src.processing.ner_extractor import extract_entities_and_relations, NERExtractor

# # Set up basic logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# def test_ner_extractor():
#     """Test the NER extractor with sample research text"""

#     # Sample research paper text for testing
#     sample_text = """
#     In their 2020 study, Dr. Jane Smith from Stanford University proposed a novel machine learning framework
#     called NeuroLearn for analyzing neurological data. The research was conducted in collaboration with
#     researchers at MIT and Harvard Medical School. The methodology combines convolutional neural networks
#     with attention mechanisms, achieving 95% accuracy on the Alzheimer's Disease dataset.
#     This approach significantly outperforms traditional methods like SVM and random forests.
#     """

#     print("Testing NER Extractor...")
#     print("=" * 50)

#     # Test spaCy extraction
#     print("\n🧪 Testing spaCy NER Extraction")
#     extractor = NERExtractor()
#     extractor.extraction_method = "spacy"

#     try:
#         entities, relations = await extractor.extract_entities_and_relations(sample_text)
#         print(f"✅ spaCy extraction successful")
#         print(f"👤 Entities found: {len(entities)}")
#         for entity in entities:
#             print(f"   - {entity.text} ({entity.type}, confidence: {entity.confidence})")

#         print(f"🔗 Relations found: {len(relations)}")
#         for relation in relations[:3]:  # Show first 3 relations
#             print(f"   - {relation.source_entity.text} → {relation.target_entity.text} ({relation.relationship})")

#     except Exception as e:
#         print(f"❌ spaCy extraction failed: {e}")

#     # Test LLM extraction (if configured)
#     print("\n🧪 Testing LLM NER Extraction")
#     extractor.extraction_method = "llm"

#     try:
#         entities, relations = await extractor.extract_entities_and_relations(sample_text)
#         print(f"✅ LLM extraction successful")
#         print(f"👤 Entities found: {len(entities)}")
#         for entity in entities:
#             print(f"   - {entity.text} ({entity.type}, confidence: {entity.confidence})")

#         print(f"🔗 Relations found: {len(relations)}")
#         for relation in relations[:3]:
#             print(f"   - {relation.source_entity.text} → {relation.target_entity.text} ({relation.relationship})")

#     except Exception as e:
#         print(f"❌ LLM extraction failed: {e}")
#         print("💡 Note: LLM extraction requires Vertex AI configuration")

# def test_entity_mapping():
#     """Test spaCy entity type mapping"""
#     print("\n🧪 Testing Entity Type Mapping")

#     extractor = NERExtractor()

#     # Test spaCy entity type mapping
#     test_cases = [
#         ("PERSON", "person"),
#         ("ORG", "organization"),
#         ("GPE", "location"),
#         ("PRODUCT", "concept"),
#         ("UNKNOWN_TYPE", "concept")  # Default mapping
#     ]

#     for spacy_type, expected_type in test_cases:
#         mapped_type = extractor._map_spacy_entity_type(spacy_type)
#         status = "✅" if mapped_type == expected_type else "❌"
#         print(f"{status} {spacy_type} → {mapped_type} (expected: {expected_type})")

# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(test_ner_extractor())
#     test_entity_mapping()
