# test_kg_gen.py
import asyncio
import sys
import os

# Add the src directory to the path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append('../')

from src.processing.kg_gen_extractor import KGGENExtractor


async def main():
    print("🧪 Testing KG-Gen Extractor...")

    test_text = "Linda is Josh's mother. Ben is Josh's brother. Andrew is Josh's father."

    try:
        extractor = KGGENExtractor()
        print("✅ KG-Gen initialized successfully")

        entities, relations = await extractor.extract_entities_and_relations(
            test_text)
        print(
            f"✅ Extraction successful: Found {len(entities)} entities and {len(relations)} relations"
        )

        # Print results
        if entities:
            print("\n--- Entities ---")
            for entity in entities:
                print(f"  - {entity.text} ({entity.type})")

        if relations:
            print("\n--- Relations ---")
            for relation in relations:
                print(
                    f"  - {relation.source_entity.text} --{relation.relationship}--> {relation.target_entity.text}"
                )

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
