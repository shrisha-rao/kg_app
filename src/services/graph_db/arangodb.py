# src/services/graph_db/arangodb.py
import logging
from typing import List, Dict, Any, Optional
from arango import ArangoClient
from arango.exceptions import ArangoError
from datetime import datetime

from .base import GraphDBService, Node, Edge, GraphQueryResult
from src.config import settings

logger = logging.getLogger(__name__)


class ArangoDBService(GraphDBService):
    """ArangoDB implementation of the graph database service"""

    def __init__(self):
        self.host = settings.arangodb_host
        self.username = settings.arangodb_username
        self.password = settings.arangodb_password
        self.database_name = settings.arangodb_database
        self.client = None
        self.db = None
        logger.info(f"Initialized ArangoDB service with host: {self.host}")

    async def connect(self) -> bool:
        """Connect to ArangoDB"""
        try:
            # Initialize the ArangoDB client
            self.client = ArangoClient(hosts=self.host)

            # Connect to the _system database to manage other databases
            sys_db = self.client.db(name="_system",
                                    username=self.username,
                                    password=self.password)

            # Check if the target database exists; if not, create it
            if not sys_db.has_database(self.database_name):
                #print('creating ')
                sys_db.create_database(self.database_name)
                logger.info(f"Created new database: {self.database_name}")

            # Now, connect to the correct database
            self.db = self.client.db(name=self.database_name,
                                     username=self.username,
                                     password=self.password)

            # self._initialize_graph(self.db)

            logger.info(
                f"Connected to ArangoDB database: {self.database_name}")
            return True

        except ArangoError as e:
            self.db = None
            logger.error(f"Error connecting to ArangoDB: {e}")
            return False

    # async def connect(self) -> bool:
    #     """Connect to ArangoDB"""
    #     try:
    #         # Initialize the ArangoDB client
    #         self.client = ArangoClient(hosts=self.host)

    #         # Connect to the database
    #         self.db = self.client.db(name=self.database_name,
    #                                  username=self.username,
    #                                  password=self.password)

    #         logger.info(
    #             f"Connected to ArangoDB database: {self.database_name}")
    #         return True

    #     except ArangoError as e:
    #         logger.error(f"Error connecting to ArangoDB: {e}")
    #         return False

    async def disconnect(self) -> bool:
        """Disconnect from ArangoDB"""
        try:
            if self.client:
                self.client.close()
                logger.info("Disconnected from ArangoDB")
                return True
            return False

        except ArangoError as e:
            logger.error(f"Error disconnecting from ArangoDB: {e}")
            return False

    async def upsert_node(self, node: Node) -> bool:
        """Insert or update a node in ArangoDB"""
        try:
            collection_name = f"nodes_{node.type}"

            if not self.db.has_collection(collection_name):
                self.db.create_collection(collection_name)

            collection = self.db.collection(collection_name)

            # Prepare document
            document = {
                "_key": node.id.split("/")[-1],
                "label": node.label,
                **node.properties, "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }

            # Upsert the document
            try:
                # collection.upsert({"_key": node.id}, document, return_new=False)
                collection.insert(document, overwrite=True)

                # logger.debug(
                #     f"Upserted node: {node.id} in collection: {collection_name}"
                # )
                return True
            except ArangoError as err:
                logger.error(
                    f"Failed to INSERT/UPDATE document {node.id}: {err}")
                return False
            return True

        except ArangoError as e:
            logger.error(f"Error upserting node in ArangoDB: {e}")
            return False

    async def upsert_edge(self, edge: Edge) -> bool:
        """Insert or update an edge in ArangoDB"""
        try:
            collection_name = f"edges_{edge.type}"

            # Ensure the edge collection exists
            if not self.db.has_collection(collection_name):
                self.db.create_collection(collection_name, edge=True)

            collection = self.db.collection(collection_name)

            # Prepare edge document
            document = {
                "_key": edge.id.split("/")[-1],
                "_from": edge.source_id,
                "_to": edge.target_id,
                "label": edge.label,
                **edge.properties, "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }

            # Upsert the edge
            # collection.upsert({"_key": edge.id}, document, return_new=False)
            # Use insert with overwrite=True to achieve an upsert
            collection.insert(document, overwrite=True)

            # logger.debug(
            #     f"Upserted edge: {edge.id} in collection: {collection_name}")
            return True

        except ArangoError as e:
            logger.error(f"Error upserting edge in ArangoDB: {e}")
            return False

    async def get_node(self, node_id: str) -> Optional[Node]:
        """Get a node by ID from ArangoDB"""
        try:
            # Node ID format: collection_name/key
            if '/' in node_id:
                collection_name, key = node_id.split('/', 1)
            else:
                # Try to find the node in any collection
                collections = [
                    col for col in self.db.collections()
                    if col['name'].startswith('nodes_')
                ]
                for col_info in collections:
                    collection = self.db.collection(col_info['name'])
                    if collection.has(node_id):
                        collection_name = col_info['name']
                        key = node_id
                        break
                else:
                    return None

            collection = self.db.collection(collection_name)
            document = collection.get(key)

            if document:
                node_type = collection_name.replace('nodes_', '')
                properties = {
                    k: v
                    for k, v in document.items() if k not in [
                        '_key', '_id', '_rev', 'label', 'created_at',
                        'updated_at'
                    ]
                }

                return Node(id=document['_id'],
                            label=document.get('label', ''),
                            properties=properties,
                            type=node_type)

                # return Node(id=document['_key'],
                #             label=document.get('label', ''),
                #             properties=properties,
                #             type=node_type)

            return None

        except ArangoError as e:
            logger.error(f"Error getting node from ArangoDB: {e}")
            return None

    async def get_nodes_by_ids(self, node_ids: List[str]) -> List[Node]:
        """Retrieves full node objects for a list of node IDs."""
        if not node_ids:
            return []

        # We use a custom AQL query to retrieve all documents by their _id
        query = f"""
        FOR doc_id IN @node_ids
          LET parts = SPLIT(doc_id, '/')
          LET collection = parts[0]
          LET key = parts[1]
          RETURN DOCUMENT(collection, key)
        """

        # Execute the query and map the results back to your Node model
        # (Assuming execute_query returns raw dicts)
        raw_results = await self.execute_query(query,
                                               params={"node_ids": node_ids})

        # You'll need logic here to convert raw ArangoDB documents to your Node model
        # For simplicity, assume raw_results.nodes contains the hydrated Node objects
        return raw_results.nodes

    async def get_edge(self, edge_id: str) -> Optional[Edge]:
        """Get an edge by ID from ArangoDB"""
        try:
            # Edge ID format: collection_name/key
            if '/' in edge_id:
                collection_name, key = edge_id.split('/', 1)
            else:
                # Try to find the edge in any collection
                collections = [
                    col for col in self.db.collections()
                    if col['name'].startswith('edges_')
                ]
                for col_info in collections:
                    collection = self.db.collection(col_info['name'])
                    if collection.has(edge_id):
                        collection_name = col_info['name']
                        key = edge_id
                        break
                else:
                    return None

            collection = self.db.collection(collection_name)
            document = collection.get(key)

            if document:
                edge_type = collection_name.replace('edges_', '')
                properties = {
                    k: v
                    for k, v in document.items() if k not in [
                        '_key', '_id', '_rev', '_from', '_to', 'label',
                        'created_at', 'updated_at'
                    ]
                }

                return Edge(
                    id=document['_id'],  #['_key'],
                    source_id=document['_from'],
                    target_id=document['_to'],
                    label=document.get('label', ''),
                    properties=properties,
                    type=edge_type)

            return None

        except ArangoError as e:
            logger.error(f"Error getting edge from ArangoDB: {e}")
            return None

    async def query_nodes(self,
                          label: Optional[str] = None,
                          properties: Optional[Dict[str, Any]] = None,
                          limit: int = 100) -> List[Node]:
        """Query nodes by label and/or properties in ArangoDB"""
        try:
            # This is a simplified implementation
            # In a real implementation, you would use AQL queries
            collections = [
                col for col in self.db.collections()
                if col['name'].startswith('nodes_')
            ]
            results = []

            for col_info in collections:
                collection = self.db.collection(col_info['name'])
                node_type = col_info['name'].replace('nodes_', '')

                # Build filter conditions
                filters = []
                if label:
                    # Filter by label (assuming label is always a string and needs case-insensitive matching)
                    filters.append(f"LOWER(doc.label) == LOWER('{label}')")
                    # filters.append(f"doc.label == '{label}'")
                if properties:
                    for key, value in properties.items():
                        if isinstance(value, str):
                            # Use LOWER() for case-insensitive matching in AQL for strings
                            # repr(value) ensures the string is correctly quoted for AQL
                            filters.append(
                                f"LOWER(doc.{key}) == LOWER({repr(value)})")
                        else:
                            # For non-strings (numbers, booleans), use strict equality
                            filters.append(f"doc.{key} == {repr(value)}")
                        # filters.append(f"doc.{key} == {repr(value)}")

                # Build AQL query
                filter_str = " AND ".join(filters) if filters else "true"
                query = f"""
                FOR doc IN {collection.name}
                FILTER {filter_str}
                LIMIT {limit}
                RETURN doc
                """
                cursor = self.db.aql.execute(query)
                for doc in cursor:
                    doc_properties = {
                        k: v
                        for k, v in doc.items() if k not in [
                            '_key', '_id', '_rev', 'label', 'created_at',
                            'updated_at'
                        ]
                    }

                    results.append(
                        Node(
                            id=doc['_id'],  #['_key'],
                            label=doc.get('label', ''),
                            properties=doc_properties,
                            type=node_type))

            return results

        except ArangoError as e:
            logger.error(f"Error querying nodes in ArangoDB: {e}")
            return []

    async def query_edges(self,
                          label: Optional[str] = None,
                          properties: Optional[Dict[str, Any]] = None,
                          limit: int = 100) -> List[Edge]:
        """Query edges by label and/or properties in ArangoDB"""
        try:
            # This is a simplified implementation
            collections = [
                col for col in self.db.collections()
                if col['name'].startswith('edges_')
            ]
            results = []

            for col_info in collections:
                collection = self.db.collection(col_info['name'])
                edge_type = col_info['name'].replace('edges_', '')

                # Build filter conditions
                filters = []
                if label:
                    filters.append(f"doc.label == '{label}'")
                if properties:
                    for key, value in properties.items():
                        filters.append(f"doc.{key} == {repr(value)}")

                # Build AQL query
                filter_str = " AND ".join(filters) if filters else "true"
                query = f"""
                FOR doc IN {collection.name}
                FILTER {filter_str}
                LIMIT {limit}
                RETURN doc
                """

                cursor = self.db.aql.execute(query)
                for doc in cursor:
                    doc_properties = {
                        k: v
                        for k, v in doc.items() if k not in [
                            '_key', '_id', '_rev', '_from', '_to', 'label',
                            'created_at', 'updated_at'
                        ]
                    }

                    results.append(
                        Edge(
                            id=doc['_id'],  #['_key'],
                            source_id=doc['_from'],
                            target_id=doc['_to'],
                            label=doc.get('label', ''),
                            properties=doc_properties,
                            type=edge_type))

            return results

        except ArangoError as e:
            logger.error(f"Error querying edges in ArangoDB: {e}")
            return []

    async def traverse(
            self,
            start_node_id: str,
            min_depth: int = 1,
            max_depth: int = 3,
            direction: str = "any",
            edge_labels: Optional[List[str]] = None) -> GraphQueryResult:
        """Traverse the graph from a starting node in ArangoDB"""
        try:
            # Build AQL query for traversal
            edge_filter = ""
            if edge_labels:
                edge_labels_str = ", ".join([f"'{l}'" for l in edge_labels])
                edge_filter = f"FILTER edge.label IN [{edge_labels_str}]"

            direction_map = {
                "outbound": "OUTBOUND",
                "inbound": "INBOUND",
                "any": "ANY"
            }
            aql_direction = direction_map.get(direction, "ANY")

            query = f"""
            FOR vertex, edge, path IN {min_depth}..{max_depth} {aql_direction}
            '{start_node_id}' GRAPH 'knowledge_graph'
            {edge_filter}
            RETURN {{vertex: vertex, edge: edge}}
            """

            logger.info("x" * 51)
            logger.info("x" * 51)
            logger.info(f"{query}")
            logger.info("x" * 51)
            logger.info("x" * 51)

            start_time = datetime.now()
            cursor = self.db.aql.execute(query)
            execution_time = (datetime.now() - start_time).total_seconds()

            nodes = []
            edges = []

            for result in cursor:
                if 'vertex' in result:
                    vertex = result['vertex']
                    node_type = vertex['_id'].split('/')[0].replace(
                        'nodes_', '')
                    properties = {
                        k: v
                        for k, v in vertex.items() if k not in [
                            '_key', '_id', '_rev', 'label', 'created_at',
                            'updated_at'
                        ]
                    }

                    nodes.append(
                        Node(
                            id=vertex['_id'],  #vertex['_key'],
                            label=vertex.get('label', ''),
                            properties=properties,
                            type=node_type))

                if 'edge' in result:
                    edge = result['edge']
                    edge_type = edge['_id'].split('/')[0].replace('edges_', '')
                    properties = {
                        k: v
                        for k, v in edge.items() if k not in [
                            '_key', '_id', '_rev', '_from', '_to', 'label',
                            'created_at', 'updated_at'
                        ]
                    }

                    edges.append(
                        Edge(
                            id=edge['_id'],  #['_key'],
                            source_id=edge['_from'],
                            target_id=edge['_to'],
                            label=edge.get('label', ''),
                            properties=properties,
                            type=edge_type))

            return GraphQueryResult(nodes=nodes,
                                    edges=edges,
                                    execution_time=execution_time)

        except ArangoError as e:
            logger.error(f"Error traversing graph in ArangoDB: {e}")
            return GraphQueryResult(nodes=[], edges=[], execution_time=0)

    async def delete_node(self, node_id: str) -> bool:
        """Delete a node and its edges from ArangoDB"""
        try:
            # Node ID format: collection_name/key
            if '/' in node_id:
                collection_name, key = node_id.split('/', 1)
            else:
                # Try to find the node in any collection
                collections = [
                    col for col in self.db.collections()
                    if col['name'].startswith('nodes_')
                ]
                for col_info in collections:
                    collection = self.db.collection(col_info['name'])
                    if collection.has(node_id):
                        collection_name = col_info['name']
                        key = node_id
                        break
                else:
                    return False

            collection = self.db.collection(collection_name)
            collection.delete(key)

            logger.info(f"Deleted node: {node_id}")
            return True

        except ArangoError as e:
            logger.error(f"Error deleting node from ArangoDB: {e}")
            return False

    async def delete_edge(self, edge_id: str) -> bool:
        """Delete an edge from ArangoDB"""
        try:
            # Edge ID format: collection_name/key
            if '/' in edge_id:
                collection_name, key = edge_id.split('/', 1)
            else:
                # Try to find the edge in any collection
                collections = [
                    col for col in self.db.collections()
                    if col['name'].startswith('edges_')
                ]
                for col_info in collections:
                    collection = self.db.collection(col_info['name'])
                    if collection.has(edge_id):
                        collection_name = col_info['name']
                        key = edge_id
                        break
                else:
                    return False

            collection = self.db.collection(collection_name)
            collection.delete(key)

            logger.info(f"Deleted edge: {edge_id}")
            return True

        except ArangoError as e:
            logger.error(f"Error deleting edge from ArangoDB: {e}")
            return False

    async def execute_query(
            self,
            query: str,
            params: Optional[Dict[str, Any]] = None) -> GraphQueryResult:
        """Execute a custom AQL query in ArangoDB"""
        try:
            start_time = datetime.now()
            cursor = self.db.aql.execute(query, bind_vars=params or {})
            execution_time = (datetime.now() - start_time).total_seconds()

            nodes = []
            edges = []

            for result in cursor:
                # This is a simplified implementation
                # In a real implementation, you would parse the result based on the query
                if '_id' in result and result['_id'].startswith('nodes_'):
                    node_type = result['_id'].split('/')[0].replace(
                        'nodes_', '')
                    properties = {
                        k: v
                        for k, v in result.items() if k not in [
                            '_key', '_id', '_rev', 'label', 'created_at',
                            'updated_at'
                        ]
                    }

                    nodes.append(
                        Node(
                            id=result['_id'],  # result['_key'],
                            label=result.get('label', ''),
                            properties=properties,
                            type=node_type))
                elif '_id' in result and result['_id'].startswith('edges_'):
                    edge_type = result['_id'].split('/')[0].replace(
                        'edges_', '')
                    properties = {
                        k: v
                        for k, v in result.items() if k not in [
                            '_key', '_id', '_rev', '_from', '_to', 'label',
                            'created_at', 'updated_at'
                        ]
                    }

                    edges.append(
                        Edge(id=result['_key'],
                             source_id=result['_from'],
                             target_id=result['_to'],
                             label=result.get('label', ''),
                             properties=properties,
                             type=edge_type))

            return GraphQueryResult(nodes=nodes,
                                    edges=edges,
                                    execution_time=execution_time)

        except ArangoError as e:
            logger.error(f"Error executing AQL query in ArangoDB: {e}")
            return GraphQueryResult(nodes=[], edges=[], execution_time=0)

    # def _initialize_graph(self, db_handler):
    #     """Initializes or updates the ResearchGraph with all current edges_* collections."""
    #     GRAPH_NAME = "ResearchGraph"

    #     # 1. Drop the graph if it exists to ensure a clean, conflict-free recreation
    #     if db_handler.has_graph(GRAPH_NAME):
    #         db_handler.delete_graph(GRAPH_NAME, drop_collections=False)
    #         logger.info(f"Existing graph '{GRAPH_NAME}' dropped successfully.")

    #     # 1a. Get all collection names from the database
    #     # Note: You'll need to check the arango.db API for the exact method to list collections.
    #     # It's typically a synchronous call on the db_handler object.
    #     all_collections = db_handler.collections()

    #     # 2. Filter for edge collections
    #     edge_collections = [
    #         c['name'] for c in all_collections
    #         if c['name'].startswith('edges_')
    #     ]

    #     # 3. Define all possible node collections for the graph structure
    #     # (Based on your known node prefixes)
    #     vertex_collections = [
    #         'nodes_concept', 'nodes_location', 'nodes_methodology',
    #         'nodes_organization', 'nodes_paper', 'nodes_person'
    #         # Add any other nodes_* collections you might have
    #     ]

    #     # 4. Create the edge definitions list
    #     edge_definitions = []
    #     for edge_col in edge_collections:
    #         # We assume any edge can connect any node type for simplicity/robustness
    #         edge_definitions.append({
    #             'edge_collection': edge_col,
    #             'from_vertex_collections': vertex_collections,
    #             'to_vertex_collections': vertex_collections
    #         })

    #     if not edge_definitions:
    #         logger.warning(
    #             "No edge collections found to define the graph. Skipping graph creation."
    #         )
    #         return

    #     # 5. Create or Replace the Named Graph
    #     if db_handler.has_graph(GRAPH_NAME):
    #         logger.info(
    #             f"Graph '{GRAPH_NAME}' already exists. Attempting to update definitions."
    #         )
    #         # Note: Updating graph definitions is complex. The safest approach is often
    #         # to delete and recreate, or check for specific driver methods to update.
    #         # For simplicity in this answer, we'll recreate if needed.

    #         # Use the graph handler to replace its definitions
    #         graph = db_handler.graph(GRAPH_NAME)
    #         # The python-arango driver might have an update method, but for robust setup,
    #         # ensuring all edges are present on first run is key.
    #         # If you trust your initial setup, you can skip this block.

    #     else:
    #         db_handler.create_graph(GRAPH_NAME,
    #                                 edge_definitions=edge_definitions)
    #         logger.info(
    #             f"Successfully created graph '{GRAPH_NAME}' with {len(edge_collections)} edge collections."
    #         )
