# src/scripts/init_graph_db.py
#!/usr/bin/env python3
"""
Script to initialize the ArangoDB graph database with required collections and indexes.
"""

import logging
import sys
import asyncio
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.graph_db import get_graph_db_service
from src.config import settings

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class GraphDBInitializer:
    """Initialize the graph database with required structure"""

    def __init__(self):
        self.graph_db = get_graph_db_service()

    async def initialize(self):
        """Initialize the graph database"""
        try:
            logger.info("Starting graph database initialization...")

            # Connect to the database
            if not await self.graph_db.connect():
                logger.error("Failed to connect to graph database")
                return False

            # Create node collections
            await self._create_node_collections()

            # Create edge collections
            await self._create_edge_collections()

            # Create graph (if using named graphs)
            await self._create_knowledge_graph()

            # Create indexes
            await self._create_indexes()

            logger.info("Graph database initialization completed successfully")
            return True

        except Exception as e:
            logger.error(f"Error initializing graph database: {e}")
            return False
        finally:
            await self.graph_db.disconnect()

    async def _create_node_collections(self):
        """Create node collections for different entity types"""
        node_collections = [
            "nodes_paper", "nodes_person", "nodes_organization",
            "nodes_location", "nodes_concept", "nodes_methodology"
        ]

        for collection_name in node_collections:
            try:
                # Check if collection exists
                collections = [
                    col for col in self.graph_db.db.collections()
                    if col['name'] == collection_name
                ]

                if not collections:
                    self.graph_db.db.create_collection(collection_name)
                    logger.info(f"Created node collection: {collection_name}")
                else:
                    logger.info(
                        f"Node collection already exists: {collection_name}")

            except Exception as e:
                logger.error(
                    f"Error creating node collection {collection_name}: {e}")

    async def _create_edge_collections(self):
        """Create edge collections for different relationship types"""
        edge_collections = [
            ("edges_cites", "CITATION relationships between papers"),
            ("edges_authored_by",
             "AUTHOR relationships between papers and people"),
            ("edges_contains",
             "CONTAINS relationships between papers and entities"),
            ("edges_related_to", "GENERIC relationships between entities"),
            ("edges_belongs_to",
             "MEMBERSHIP relationships (e.g., person to organization)"),
            ("edges_located_at", "LOCATION relationships"),
            ("edges_uses",
             "USAGE relationships (e.g., paper uses methodology)")
        ]

        for collection_name, description in edge_collections:
            try:
                # Check if collection exists
                collections = [
                    col for col in self.graph_db.db.collections()
                    if col['name'] == collection_name
                ]

                if not collections:
                    self.graph_db.db.create_collection(collection_name,
                                                       edge=True)
                    logger.info(
                        f"Created edge collection: {collection_name} - {description}"
                    )
                else:
                    logger.info(
                        f"Edge collection already exists: {collection_name}")

            except Exception as e:
                logger.error(
                    f"Error creating edge collection {collection_name}: {e}")

    # async def _create_knowledge_graph_OLD(self):
    #     """Create or recreate the knowledge graph with edge definitions"""
    #     try:
    #         graph_name = settings.knowledge_graph_name

    #         # 1. Force Deletion of Existing Graph (to clear outdated definitions)
    #         if self.graph_db.db.has_graph(graph_name):
    #             logger.info(
    #                 f"Graph already exists: {graph_name}. Deleting and recreating to ensure correct definitions."
    #             )
    #             self.graph_db.db.delete_graph(graph_name)

    #         # 2. Define edge collections for the graph (Same definitions as before)
    #         edge_definitions = [{
    #             "edge_collection": "edges_cites",
    #             "from_vertex_collections": ["nodes_paper"],
    #             "to_vertex_collections": ["nodes_paper"]
    #         }, {
    #             "edge_collection": "edges_authored_by",
    #             "from_vertex_collections": ["nodes_paper"],
    #             "to_vertex_collections": ["nodes_person"]
    #         }, {
    #             "edge_collection":
    #             "edges_contains",
    #             "from_vertex_collections": ["nodes_paper"],
    #             "to_vertex_collections": [
    #                 "nodes_person", "nodes_organization", "nodes_location",
    #                 "nodes_concept", "nodes_methodology"
    #             ]
    #         }, {
    #             "edge_collection":
    #             "edges_related_to",
    #             "from_vertex_collections": [
    #                 "nodes_person", "nodes_organization", "nodes_location",
    #                 "nodes_concept", "nodes_methodology"
    #             ],
    #             "to_vertex_collections": [
    #                 "nodes_person", "nodes_organization", "nodes_location",
    #                 "nodes_concept", "nodes_methodology"
    #             ]
    #         }, {
    #             "edge_collection": "edges_belongs_to",
    #             "from_vertex_collections": ["nodes_person"],
    #             "to_vertex_collections": ["nodes_organization"]
    #         }, {
    #             "edge_collection":
    #             "edges_located_at",
    #             "from_vertex_collections":
    #             ["nodes_person", "nodes_organization"],
    #             "to_vertex_collections": ["nodes_location"]
    #         }, {
    #             "edge_collection": "edges_uses",
    #             "from_vertex_collections": ["nodes_paper"],
    #             "to_vertex_collections": ["nodes_methodology"]
    #         }]

    #         # 3. Create the graph
    #         self.graph_db.db.create_graph(graph_name, edge_definitions)
    #         logger.info(f"Created knowledge graph: {graph_name}")

    #     except Exception as e:
    #         logger.error(f"Error creating knowledge graph: {e}")

    async def _create_knowledge_graph(self):
        """Create or update the named knowledge graph with all existing edge collections."""
        #GRAPH_NAME = 'knowledge_graph'
        GRAPH_NAME = settings.knowledge_graph_name
        db_handler = self.graph_db.db  # Assume self.graph_db.db is the ArangoDB handler

        # 1. FORCE DELETE (MANDATORY FIX)
        if db_handler.has_graph(GRAPH_NAME):
            logger.info(
                f"Graph '{GRAPH_NAME}' already exists. Attempting to delete before recreation."
            )
        try:
            # Drop and recreate is the safest way to update definitions
            db_handler.delete_graph(GRAPH_NAME, ignore_missing=True)
            logger.info(f"Deleted old graph '{GRAPH_NAME}'.")
        except Exception as e:
            # If deletion fails, we log the error but allow the creation to attempt,
            # though it will likely fail with ERR 1921.
            logger.error(
                f"Failed to delete graph '{GRAPH_NAME}': {e}. Stopping creation."
            )
            # Return False to propagate the failure up to the initialize method
            return False

        # 1. Identify all edge collections
        edge_collections = [
            col['name'] for col in db_handler.collections()
            if col['name'].startswith('edges_')
        ]

        # 2. Identify all vertex collections (assuming all are potential vertices)
        vertex_collections = [
            col['name'] for col in db_handler.collections()
            if col['name'].startswith('nodes_')
            or col['name'].startswith('entities')
            # Add 'entities' explicitly if it's used as a collection name
        ]

        # 3. Build edge definitions (a definition for every edge collection)
        edge_definitions = []
        if edge_collections and vertex_collections:
            for edge_col in edge_collections:
                edge_definitions.append({
                    'edge_collection':
                    edge_col,
                    'from_vertex_collections':
                    vertex_collections,
                    'to_vertex_collections':
                    vertex_collections
                })

        if not edge_definitions:
            logger.warning(
                "No edge collections found to define the graph. Skipping graph creation."
            )
            return

        # 4. Create or Replace the Named Graph
        if db_handler.has_graph(GRAPH_NAME):
            logger.info(
                f"Graph '{GRAPH_NAME}' already exists. Attempting to update definitions."
            )

            # The simplest way to ensure all definitions are applied is to drop and recreate.
            # NOTE: If you have complex graph definitions, a partial update is better,
            # but dropping is the most robust fix for missing collections.
            try:
                db_handler.delete_graph(GRAPH_NAME)
                logger.info(f"Deleted old graph '{GRAPH_NAME}'.")
            except Exception as e:
                logger.error(f"Failed to delete graph: {e}")
                return

        db_handler.create_graph(GRAPH_NAME, edge_definitions=edge_definitions)
        logger.info(
            f"Successfully created/updated graph '{GRAPH_NAME}' with {len(edge_collections)} edge collections."
        )

    # async def _create_knowledge_graph(self):
    #     """Create the knowledge graph with edge definitions"""
    #     try:
    #         graph_name = "knowledge_graph"

    #         # Check if graph already exists
    #         if self.graph_db.db.has_graph(graph_name):
    #             logger.info(f"Graph already exists: {graph_name}")
    #             return

    #         # Define edge collections for the graph
    #         edge_definitions = [{
    #             "edge_collection": "edges_cites",
    #             "from_vertex_collections": ["nodes_paper"],
    #             "to_vertex_collections": ["nodes_paper"]
    #         }, {
    #             "edge_collection": "edges_authored_by",
    #             "from_vertex_collections": ["nodes_paper"],
    #             "to_vertex_collections": ["nodes_person"]
    #         }, {
    #             "edge_collection":
    #             "edges_contains",
    #             "from_vertex_collections": ["nodes_paper"],
    #             "to_vertex_collections": [
    #                 "nodes_person", "nodes_organization", "nodes_location",
    #                 "nodes_concept", "nodes_methodology"
    #             ]
    #         }, {
    #             "edge_collection":
    #             "edges_related_to",
    #             "from_vertex_collections": [
    #                 "nodes_person", "nodes_organization", "nodes_location",
    #                 "nodes_concept", "nodes_methodology"
    #             ],
    #             "to_vertex_collections": [
    #                 "nodes_person", "nodes_organization", "nodes_location",
    #                 "nodes_concept", "nodes_methodology"
    #             ]
    #         }, {
    #             "edge_collection": "edges_belongs_to",
    #             "from_vertex_collections": ["nodes_person"],
    #             "to_vertex_collections": ["nodes_organization"]
    #         }, {
    #             "edge_collection":
    #             "edges_located_at",
    #             "from_vertex_collections":
    #             ["nodes_person", "nodes_organization"],
    #             "to_vertex_collections": ["nodes_location"]
    #         }, {
    #             "edge_collection": "edges_uses",
    #             "from_vertex_collections": ["nodes_paper"],
    #             "to_vertex_collections": ["nodes_methodology"]
    #         }]

    #         # Create the graph
    #         self.graph_db.db.create_graph(graph_name, edge_definitions)
    #         logger.info(f"Created knowledge graph: {graph_name}")

    #     except Exception as e:
    #         logger.error(f"Error creating knowledge graph: {e}")

    async def _create_indexes(self):
        """Create indexes for better query performance"""
        try:
            # Indexes for node collections
            node_indexes = [{
                "type": "persistent",
                "fields": ["label"]
            }, {
                "type": "persistent",
                "fields": ["type"]
            }, {
                "type": "persistent",
                "fields": ["created_at"]
            }, {
                "type": "persistent",
                "fields": ["owner_id"]
            }]

            # Indexes for edge collections
            edge_indexes = [{
                "type": "persistent",
                "fields": ["label"]
            }, {
                "type": "persistent",
                "fields": ["type"]
            }, {
                "type": "persistent",
                "fields": ["created_at"]
            }, {
                "type": "persistent",
                "fields": ["owner_id"]
            }]

            # Create indexes for all node collections
            node_collections = [
                col for col in self.graph_db.db.collections()
                if col['name'].startswith('nodes_')
            ]

            for col_info in node_collections:
                collection = self.graph_db.db.collection(col_info['name'])
                for index_config in node_indexes:
                    try:
                        collection.add_persistent_index(
                            fields=index_config["fields"])
                        logger.info(
                            f"Created index on {col_info['name']} for fields: {index_config['fields']}"
                        )
                    except Exception as e:
                        logger.debug(
                            f"Index may already exist on {col_info['name']}: {e}"
                        )

            # Create indexes for all edge collections
            edge_collections = [
                col for col in self.graph_db.db.collections()
                if col['name'].startswith('edges_')
            ]

            for col_info in edge_collections:
                collection = self.graph_db.db.collection(col_info['name'])
                for index_config in edge_indexes:
                    try:
                        collection.add_persistent_index(
                            fields=index_config["fields"])
                        logger.info(
                            f"Created index on {col_info['name']} for fields: {index_config['fields']}"
                        )
                    except Exception as e:
                        logger.debug(
                            f"Index may already exist on {col_info['name']}: {e}"
                        )

        except Exception as e:
            logger.error(f"Error creating indexes: {e}")

    async def check_connection(self):
        """Test database connection"""
        try:
            if await self.graph_db.connect():
                logger.info("✅ Successfully connected to ArangoDB")
                await self.graph_db.disconnect()
                return True
            else:
                logger.error("❌ Failed to connect to ArangoDB")
                return False
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False


async def main():
    """Main function"""
    initializer = GraphDBInitializer()

    # Test connection first
    if not await initializer.check_connection():
        sys.exit(1)

    # Initialize the database
    success = await initializer.initialize()

    if success:
        logger.info("🎉 Graph database initialization completed successfully!")
        sys.exit(0)
    else:
        logger.error("💥 Graph database initialization failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
