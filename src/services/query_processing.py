# src/services/query_processing.py
import logging
import json
from typing import List, Dict, Any, Optional
from src.models.query import QueryCreate, QueryResponse, QueryType, QueryScope, Citation
from src.models.paper import Paper
from src.services.vector_db import get_vector_db_service
from src.services.graph_db import get_graph_db_service
from src.services.llm import get_llm_service
from src.utils.cache import get_cache_client

from src.services.graph_db.base import GraphQueryResult, Node, Edge

# logging.basicConfig(level=logging.DEBUG)
# # or for uvicorn:
# logging.getLogger("uvicorn").setLevel(logging.DEBUG)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
"""
This implementation provides a comprehensive query processing service that:

    Handles the complete query processing pipeline from query to answer

    Integrates with all your services (vector DB, graph DB, LLM, cache)

    Supports different query types with specialized prompts

    Respects scope and privacy by searching appropriate namespaces

    Generates citations based on the referenced papers

    Includes caching to improve performance for repeated queries

    Provides follow-up questions to enhance user engagement

The service follows these steps for each query:

    Check cache for existing responses

    Generate embedding for the query

    Search for relevant papers in the vector database

    Query the knowledge graph for related entities

    Build context from the retrieved information

    Generate an answer using the LLM with a specialized prompt

    Extract citations from the answer

    Generate follow-up questions

    Cache the response for future use

   cache utility is implemented here (src/utils/cache.py). 
"""


class QueryProcessingService:
    """Service for processing user queries against the research knowledge graph"""

    def __init__(self):
        self.vector_db = get_vector_db_service()
        self.graph_db = get_graph_db_service()
        self.llm = get_llm_service()
        self.cache = get_cache_client()

    async def process_query(self, query: QueryCreate) -> QueryResponse:
        """
        Process a user query and return a response with citations
        
        Args:
            query: The query to process
            
        Returns:
            QueryResponse with answer and citations
        """
        try:
            # Check cache first
            cache_key = f"query:{query.user_id}:{hash(query.query_text)}"
            cached_response = await self.cache.get(cache_key)
            if cached_response:
                logger.info(
                    f"Returning cached response for query: {query.query_text}")
                return QueryResponse(**json.loads(cached_response))

            logger.debug("step 1: Generating query embedding")

            # Step 1: Generate query embedding
            query_embedding = await self._generate_query_embedding(
                query.query_text)

            logger.debug("step 2: Search for relevant papers in vector DB")
            # logger.debug(f"step 2a: qs: {query.scope} \n id: {query.user_id}")

            # Step 2: Search for relevant papers in vector DB
            relevant_papers = await self._search_relevant_papers(
                query_embedding, query.scope, query.user_id, top_k=10)

            logger.debug("step 3: Extract context from relevant papers")
            # Step 3: Extract context from relevant papers
            context = await self._build_context(relevant_papers,
                                                query.query_text)

            logger.debug(
                "Step 4: Query the knowledge graph for related entities")
            # Step 4: Query the knowledge graph for related entities
            logger.debug(f"Step 4a: query_text: {query.query_text}")
            logger.debug(f"Step 4b: query scope: {query.scope}")
            logger.debug(f"Step 4c: query user_id: {query.user_id}")
            logger.debug(f"Step 4d: query type: {query.query_type}")

            # Check connection status and attempt to connect if necessary
            # The first time the service runs, self.graph_db.db will be None.
            if self.graph_db.db is None:
                logger.info("Attempting to connect to Graph DB...")
                # CRITICAL: MUST AWAIT THE ASYNC CONNECT CALL
                connected = await self.graph_db.connect()
                if not connected:
                    logger.error(
                        "Failed to establish ArangoDB connection, skipping KG query."
                    )
                    # You might return an error here, or skip the KG step
                    return self._build_error_response(
                        query.query_text,
                        "Failed to connect to knowledge graph.")

            logger.debug(f"graph db name: {self.graph_db.db}")

            # COMMENTED FOR DEBUG
            graph_context = await self._query_knowledge_graph(
                query.query_text, query.scope, query.user_id)

            ##################################################

            # logger.debug(f"Step 4e: graph_context: {graph_context[:250]}")

            #graph_context2 = {'entities': ['double helix', 'DNA structure']}
            # logger.debug(f"Step 4e II: graph_context: {graph_context}")
            logger.debug("Step 5: Generate answer using LLM")
            # Step 5: Generate answer using LLM
            answer = await self._generate_answer(query.query_text, context,
                                                 graph_context,
                                                 query.query_type)

            logger.debug("Step 6: Extract citations from the answer")
            # Step 6: Extract citations from the answer
            citations = await self._extract_citations(answer, relevant_papers)

            logger.debug("Step 7: Create response")
            # Step 7: Create response
            response = QueryResponse(
                query_id=
                f"query_{hash(query.query_text)}",  # This would be a real ID in production
                answer=answer,
                citations=citations,
                confidence=0.8,  # This would be calculated based on the response
                suggested_follow_up_questions=await
                self._generate_follow_up_questions(query.query_text, answer))

            # Cache the response
            await self.cache.set(
                cache_key,
                response.json(),  # json.dumps(response.dict()),
                ex=3600)  # Cache for 1 hour

            return response

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            # Return a graceful error response
            return QueryResponse(
                query_id="error",
                answer=
                "I'm sorry, I encountered an error while processing your query. Please try again later.",
                citations=[],
                confidence=0.0,
                suggested_follow_up_questions=[])

    async def _generate_query_embedding(self, query_text: str) -> List[float]:
        """Generate embedding for the query text"""
        embeddings = await self.llm.generate_embeddings([query_text])
        return embeddings[0] if embeddings else []

    async def _search_relevant_papers(self,
                                      query_embedding: List[float],
                                      scope: QueryScope,
                                      user_id: str,
                                      top_k: int = 10) -> List[Dict[str, Any]]:
        """Search for relevant papers based on the query embedding"""
        results = []

        # Always search in user's private namespace
        user_results = await self.vector_db.search(
            query_embedding,
            top_k=top_k,
            namespace=user_id,
            filter={"metadata.is_public":
                    [True, False]}  # Get both public and private papers
        )
        results.extend(user_results)

        logger.debug(
            f"inside _search_relevant_papers: private found {len(results)}")

        # If scope includes shared or public, search in those namespaces too
        if scope in [
                QueryScope.SHARED, QueryScope.PUBLIC, QueryScope.CROSS_DOMAIN
        ]:
            # In a real implementation, you would determine which shared namespaces to search
            # For now, we'll just search the public namespace
            public_results = await self.vector_db.search(query_embedding,
                                                         top_k=top_k,
                                                         namespace="public")
            results.extend(public_results)

        logger.debug(
            f"inside _search_relevant_papers: pub found {len(results)}")
        # Remove duplicates and sort by score
        seen_ids = set()
        unique_results = []
        for result in sorted(results,
                             key=lambda x: x.get('score', 0),
                             reverse=True):
            doc_id = result.get('metadata', {}).get('doc_id')
            if doc_id and doc_id not in seen_ids:
                seen_ids.add(doc_id)
                unique_results.append(result)

        logger.debug(
            f"inside _search_relevant_papers: unique found {len(unique_results)}"
        )
        return unique_results[:top_k]

    async def _build_context(self, relevant_papers: List[Dict[str, Any]],
                             query_text: str) -> str:
        """Build context from relevant papers for the LLM"""
        context_parts = []

        for i, paper in enumerate(
                relevant_papers[:5]):  # Limit to top 5 papers for context
            metadata = paper.get('metadata', {})
            doc_id = metadata.get('doc_id')

            if not doc_id:
                continue

            # In a real implementation, you would retrieve the full text from storage
            # For now, we'll use the metadata and a placeholder for text
            context_parts.append(
                f"Paper {i+1}: {metadata.get('title', 'Unknown title')}\n"
                f"Authors: {', '.join(metadata.get('authors', []))}\n"
                f"Abstract: {metadata.get('abstract', 'No abstract available')}\n"
                f"Relevance score: {paper.get('score', 0):.3f}\n")

        if not context_parts:
            return "No relevant research papers found for this query."

        return "\n".join(context_parts)

    async def _query_knowledge_graph(self, query_text: Optional[str],
                                     scope: Optional[QueryScope],
                                     user_id: Optional[str]) -> str:
        """
        Queries the knowledge graph for related entities by finding seed nodes
        and performing a graph traversal to retrieve structured context for the LLM.
        """
        try:
            # 1. FIX: Add a safety check for uninitialized graph DB
            # Attempt to connect only if necessary (connect returns True if already connected)
            if self.graph_db is None or not await self.graph_db.connect():
                logger.warning(
                    "Knowledge Graph service is unavailable or failed to connect."
                )
                return "Knowledge Graph service is unavailable."

            # 2. Extract key entities from the query (Placeholder for LLM/NLP entity extraction)
            # entities = await self._extract_entities_from_query(query_text)

            # Temporary manual list for debugging the traversal logic
            entities_to_search = ['helix']  #, 'DNA structure']

            if not entities_to_search:
                return "No relevant entities found in the query to search."

            # 3. Find the ArangoDB Node IDs for the seed entities
            query_entity_nodes = []
            for entity_text in entities_to_search:
                # Search for nodes matching this entity text
                nodes = await self.graph_db.query_nodes(
                    # NOTE: Assuming 'nodes_concept' is the primary entity collection
                    # collection_name="nodes_concept",
                    properties={"original_text": entity_text},
                    # user_id=user_id,
                    # scope=scope,
                    limit=1  # We only need one match to start the traversal
                )

                # query_nodes returns a list of Dict[str, Any] which includes the node '_id'
                query_entity_nodes.extend(nodes)

            if not query_entity_nodes:
                return "No graph data found for the relevant entities."

            # 4. Use the found seed nodes to traverse the graph and get structured context
            # This method calls self.graph_db.traverse and converts the results to triples
            graph_context = await self._get_graph_context_triples(
                query_entity_nodes=query_entity_nodes,
                user_id=user_id,
                scope=scope)

            return graph_context

        except Exception as e:
            logger.error(f"Error querying knowledge graph: {e}")
            return "Error retrieving knowledge graph information."

    async def _query_knowledge_graph_OLD(self, query_text: str,
                                         scope: QueryScope,
                                         user_id: str) -> str:
        """Query the knowledge graph for entities and relationships related to the query"""
        try:
            # FIX: Add a safety check for uninitialized graph DB
            if self.graph_db is None:
                logger.warning("Knowledge Graph service is not initialized.")
                return "Knowledge Graph service is unavailable or failed to initialize."

            # Extract key entities from the query
            entities = await self._extract_entities_from_query(query_text)

            # ======= DUBUG ==============
            #
            #entities = ['helix']  #, 'DNA structure', 'DNA', 'helix']
            #
            # ===========================

            if not entities:
                return "No relevant entities found in the knowledge graph."

            # Query the graph for each entity
            graph_context_parts = []
            for entity in entities[:3]:  # Limit to top 3 entities
                # Search for nodes matching this entity
                nodes = await self.graph_db.query_nodes(
                    properties={"original_text": entity},
                    limit=5  # Only need one match to start traversal
                )

                if nodes:
                    graph_context_parts.append(f"Entity: {entity}")
                    for node in nodes:
                        graph_context_parts.append(
                            f"  - {node.label} ({node.type}): {node.properties}"
                        )

                    # Get relationships for the first node
                    if nodes:
                        relationships = await self.graph_db.query_edges(
                            properties={"_from": nodes[0].id}, limit=3)

                        if relationships:
                            graph_context_parts.append("  Relationships:")
                            for rel in relationships:
                                target_node = await self.graph_db.get_node(
                                    rel.target_id)
                                if target_node:
                                    graph_context_parts.append(
                                        f"    - {rel.label} -> {target_node.label}"
                                    )

            return "\n".join(
                graph_context_parts
            ) if graph_context_parts else "No graph data found for this query."

        except Exception as e:
            logger.error(f"Error querying knowledge graph: {e}")
            return "Error retrieving knowledge graph information."

    async def _extract_entities_from_query(self, query_text: str) -> List[str]:
        """Extract key entities from the query text using the LLM"""
        try:
            prompt = f"""
            Analyze the following research question and identify the 
            key entities (e.g., subjects, proper nouns, technical terms, or abbreviated terms) 
            relevant to a knowledge graph.

            QUESTION: {query_text}
            
            Return only a JSON object containing a list of strings under the key "entities". 
            Do not include any other text or explanation.
            
            ENTITIES:
            """

            # Use generate_structured_response to reliably get a list of entities
            response = await self.llm.generate_structured_response(
                prompt,
                # Defines the expected JSON structure
                response_format={"entities": ["string"]},
                temperature=0.0,
                max_tokens=100)

            # The response object is a dictionary containing the structured output
            return response.get("entities", [])

        except Exception as e:
            logger.error(f"Error extracting entities with LLM: {e}")
            # Optional: Keep a simple regex or return an empty list as a fallback
            try:
                return await self._extract_entities_from_query_SIMPLISTIC(
                    query_text)
            except Exception as e2:
                logger.error(
                    f"Error extracting entities with simplistic regex: {e}")
            return []

    async def _extract_entities_from_query_SIMPLISTIC(
            self, query_text: str) -> List[str]:
        """Extract key entities from the query text"""
        # Use a simple approach for now - in a real implementation, you might use NER
        # This is a simplified version that looks for noun phrases
        import re

        # Simple pattern to find potential entities (nouns and noun phrases)
        patterns = [
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # Title case phrases
            r'\b[A-Z][a-z]+\b',  # Title case words
            r'\b(?:method|approach|technique|algorithm|model|framework)\s+[A-Za-z]+\b',  # Technical terms
        ]

        entities = set()
        for pattern in patterns:
            matches = re.findall(pattern, query_text)
            entities.update(matches)

        return list(entities)

    def _format_triples_for_llm(self, nodes: List[Node],
                                edges: List[Edge]) -> str:
        """Converts graph query results into a structured list of triples (S-P-O)."""
        if not nodes and not edges:
            return "No structured knowledge graph context found."

        # Create a mapping from full ArangoDB ID to the entity's original text
        node_map = {
            n.id: n.properties.get('original_text', n.label)
            for n in nodes
        }

        # Also include the full ID in the map in case source/target are full IDs
        node_map.update({
            f"entities/{n.id}": n.properties.get('original_text', n.label)
            for n in nodes
        })

        triples = set()
        for edge in edges:
            source_text = node_map.get(edge.source_id, edge.source_id)
            target_text = node_map.get(edge.target_id, edge.target_id)

            # Skip paper-to-entity relations; we only want entity-entity relations for LLM reasoning
            if edge.label == 'contains':
                continue

            # Format the triple as (Source) --[Relationship]--> (Target)
            triple_str = f"({source_text}) --[{edge.label}]--> ({target_text})"
            triples.add(triple_str)

        if not triples:
            return "No direct entity-to-entity relationships found in the graph."

        context = "Extracted Knowledge Graph Context (Structured Triples):\n"
        context += "\n".join(triples)
        return context

    # async def _resolve_and_format_triples(self,
    #                                       result: GraphQueryResult) -> str:
    #     """
    #     1. Filters duplicate nodes and edges from the result.
    #     2. Resolves all unique Node IDs to their human-readable text.
    #     3. Formats the edges into human-readable triples for the LLM.
    #     """
    #     if not result.edges:
    #         return ""

    #     # 1. Filter out duplicates
    #     unique_nodes = list({n.id: n for n in result.nodes}.values())
    #     unique_edges = list({e.id: e for e in result.edges}.values())

    #     # 2. Build the list of FULL ArangoDB IDs (collection/key) for fetching
    #     all_full_ids = set()
    #     for node in unique_nodes:
    #         # Ensure we always use the full ArangoDB ID (e.g., nodes_concept/key) for the fetch
    #         if "/" in node.id:
    #             full_id = node.id
    #         else:
    #             # Reconstruct the full ID using the standardized schema: nodes_{type}/{key}
    #             full_id = f"nodes_{node.type}/{node.id}"

    #         all_full_ids.add(full_id)

    #     if not all_full_ids:
    #         return ""

    #     # 3. Fetch the full Node objects by ID
    #     resolved_nodes = await self.graph_db.get_nodes_by_ids(
    #         list(all_full_ids))

    #     if resolved_nodes is None:
    #         logger.warning(
    #             "GraphDB returned None instead of a list for node resolution. Defaulting to empty list."
    #         )
    #         resolved_nodes = []

    #     # 4. Create a map from the FULL ID (_id) to the human-readable text (label)
    #     label_map = {}
    #     for node in resolved_nodes:
    #         # FIX: Prioritize the top-level 'label' attribute, which contains the human name (e.g., "Phil. Mag.")
    #         human_readable_text = node.label

    #         # Fallback 1: Check for 'original_text' in properties (since your data has it)
    #         if not human_readable_text:
    #             human_readable_text = node.properties.get('original_text')

    #         # Fallback 2: Final fallback to the full ID if no label found
    #         if not human_readable_text:
    #             human_readable_text = node.id

    #         # The key in the map is the full ArangoDB ID (_id)
    #         label_map[node.id] = human_readable_text

    #     # 5. Format the edges into the desired triple format
    #     formatted_triples = []
    #     for edge in unique_edges:  # Use unique_edges to avoid double-printing
    #         # edge.source_id and edge.target_id are the full ArangoDB IDs
    #         source_label = label_map.get(edge.source_id, edge.source_id)
    #         target_label = label_map.get(edge.target_id, edge.target_id)

    #         # Format: ("Source Text") --[Relationship Label]--> ("Target Text")
    #         triple = f'("{source_label}") --[{edge.label}]--> ("{target_label}")'
    #         formatted_triples.append(triple)

    #     # 6. Cleaned up logging for verification
    #     logger.debug("--- Knowledge Graph Context Triples (Snippet) ---")
    #     logger.debug(
    #         f"Generated {len(formatted_triples)} triples. Resolved labels for {len(resolved_nodes)} nodes."
    #     )
    #     for triple in formatted_triples[:3]:  # Log a few for verification
    #         logger.debug(triple)
    #     logger.debug("-------------------------------------------------")

    #     return "\n".join(formatted_triples)

    async def _resolve_and_format_triples(self,
                                          result: GraphQueryResult) -> str:
        """
        1. Filters duplicate nodes and edges from the result.
        2. Resolves all unique Node IDs to their human-readable text.
        3. Formats the edges into human-readable triples for the LLM.
        """
        if not result.edges:
            return ""

        # 1. Filter out duplicates
        unique_nodes = list({n.id: n for n in result.nodes}.values())
        unique_edges = list({e.id: e for e in result.edges}.values())

        # 2. Build the list of FULL ArangoDB IDs (collection/key) for fetching
        all_full_ids = set()
        for node in unique_nodes:
            # Ensure we always use the full ArangoDB ID (e.g., nodes_concept/key) for the fetch
            if "/" in node.id:
                full_id = node.id
            else:
                # Reconstruct the full ID using the standardized schema: nodes_{type}/{key}
                full_id = f"nodes_{node.type}/{node.id}"

            all_full_ids.add(full_id)

        if not all_full_ids:
            return ""

        # 3. Fetch the full Node objects by ID
        resolved_nodes = await self.graph_db.get_nodes_by_ids(
            list(all_full_ids))

        if resolved_nodes is None:
            logger.warning(
                "GraphDB returned None instead of a list for node resolution. Defaulting to empty list."
            )
            resolved_nodes = []

        # 4. Create a map from the FULL ID (_id) to the human-readable text (label)
        label_map = {}
        for node in resolved_nodes:
            # FIX: Prioritize the top-level 'label' attribute, which contains the human name (e.g., "helix")
            human_readable_text = node.label
            # Fallback 1: Check for 'original_text' in properties
            if not human_readable_text:
                human_readable_text = node.properties.get('original_text')

            # B. Get the correct FULL ID (_id) for the map key
            # The node object returned from the database should have its full ID.
            # Fallback to reconstructing the full ID if node.id is somehow the _key.
            full_node_id = node.id
            if "/" not in full_node_id:
                # If node.id is the short key, reconstruct the full ID
                full_node_id = f"nodes_{node.type}/{node.id}"
            else:
                # If it already contains a '/', it's a full ID (the result of the arangodb.py fix)
                full_node_id = node.id

            # C. Final fallback for label text
            if not human_readable_text:
                human_readable_text = full_node_id

            # # Fallback 2: Final fallback to the full ID if no label found
            # if not human_readable_text:
            #     human_readable_text = node.id

            # The key in the map is the full ArangoDB ID (_id)
            # Note: If the ID fix in arangodb.py is applied, node.id is the full ID here
            label_map[full_node_id] = human_readable_text

        # 5. Format the edges into the desired triple format
        formatted_triples = []
        for edge in unique_edges:
            source_label = label_map.get(edge.source_id, edge.source_id)
            target_label = label_map.get(edge.target_id, edge.target_id)

            # Format: ("Source Text") --[Relationship Label]--> ("Target Text")
            triple = f'("{source_label}") --[{edge.label}]--> ("{target_label}")'
            formatted_triples.append(triple)

        # 6. Cleaned up logging for verification
        logger.debug("--- Knowledge Graph Context Triples (Snippet) ---")
        logger.debug(
            f"Generated {len(formatted_triples)} triples. Resolved labels for {len(resolved_nodes)} nodes."
        )
        for triple in formatted_triples[:20]:
            logger.debug(triple)
        logger.debug("-------------------------------------------------")

        return "\n".join(formatted_triples)

    async def _get_graph_context_triples(self, query_entity_nodes: List[Node],
                                         user_id: str,
                                         scope: QueryScope) -> str:
        """
        Traverses the graph starting from the discovered seed entities, merges the results,
        and formats them as human-readable text triples for the LLM.
        """
        full_graph_context = GraphQueryResult(nodes=[],
                                              edges=[],
                                              execution_time=0.0)

        # Set max traversal depth (e.g., 2 hops away)
        TRAVERSAL_DEPTH = 2

        # Iterate over discovered entities and traverse the graph for each
        for entity_node in query_entity_nodes:
            # Construct the full ArangoDB _id (e.g., nodes_concept/key)
            # Ensure 'entity_node.type' is correctly set to 'concept', 'paper', etc.

            logger.debug(f"entity_node: {entity_node}")
            logger.debug(f"entity_node_ID: {entity_node.id}")
            # if "/" not in entity_node:
            #     final_start_node_id = f"nodes_{entity_node.type}/{entity_node.id}"
            # else:
            #     final_start_node_id = entity_node.id

            final_start_node_id = entity_node.id
            # @

            # if "/" in start_node_id:
            #     # If the ID already contains a slash, it's the full ArangoDB ID.
            #     final_start_node_id = start_node_id
            # else:
            #     # If it is just the short key, reconstruct the full ID.
            #     final_start_node_id = f"nodes_{entity_node.type}/{start_node_id}"

            logger.debug(
                f"Traversing graph starting from node: {final_start_node_id}")

            try:
                result = await self.graph_db.traverse(
                    start_node_id=final_start_node_id,
                    min_depth=1,
                    max_depth=TRAVERSAL_DEPTH,
                    direction="any")

                # Merge results for all starting nodes
                full_graph_context.nodes.extend(result.nodes)
                full_graph_context.edges.extend(result.edges)

            except Exception as e:
                logger.error(
                    f"Error during graph traversal from {start_node_id}: {e}")
                # Log and continue to the next entity if one fails

        # Pass the entire merged context object to the resolver
        return await self._resolve_and_format_triples(full_graph_context)

    # async def _get_graph_context_triples(
    #         self,
    #         query_entity_nodes: List[
    #             Node],  # Correct type hint based on implementation
    #         user_id: str,
    #         scope: QueryScope) -> str:
    #     """
    #     Traverses the graph starting from the discovered seed entities and
    #     formats the result as text triples for the LLM.
    #     """
    #     full_graph_context = GraphQueryResult(nodes=[],
    #                                           edges=[],
    #                                           execution_time=0.0)

    #     # Set max traversal depth (e.g., 2 hops away)
    #     TRAVERSAL_DEPTH = 2

    #     # FIX: Iterate over Node objects and use dot notation (.id, .type)
    #     for entity_node in query_entity_nodes:
    #         # Construct the full ArangoDB ID for traversal (e.g., nodes_concept/key)
    #         # We assume the collection name is based on the node's type: nodes_{type}
    #         start_node_id = f"nodes_{entity_node.type}/{entity_node.id}"
    #         # start_node_id = f"entities/{entity_node.id}"

    #         logger.debug(
    #             f"Traversing graph starting from node: {start_node_id}")

    #         result = await self.graph_db.traverse(start_node_id=start_node_id,
    #                                               min_depth=1,
    #                                               max_depth=TRAVERSAL_DEPTH,
    #                                               direction="any")

    #         # Merge results for all starting nodes
    #         full_graph_context.nodes.extend(result.nodes)
    #         full_graph_context.edges.extend(result.edges)

    #     # Filter out duplicates after merging
    #     unique_nodes = list({n.id: n
    #                          for n in full_graph_context.nodes}.values())
    #     unique_edges = list({e.id: e
    #                          for e in full_graph_context.edges}.values())

    #     return self._format_triples_for_llm(unique_nodes, unique_edges)

    async def _get_graph_context_triples_OLD(self, query_entity_nodes: List[
        Dict[str, Any]], user_id: str, scope: QueryScope) -> str:
        """
        Traverses the graph starting from the discovered seed entities and
        formats the result as text triples for the LLM.
        """
        full_graph_context = GraphQueryResult(nodes=[],
                                              edges=[],
                                              execution_time=0.0)

        # Set max traversal depth (e.g., 2 hops away)
        TRAVERSAL_DEPTH = 2

        for entity_doc in query_entity_nodes:
            start_node_id = entity_doc['_id']

            # NOTE: We skip privacy filters here because the query_nodes already
            # respected them by using a scope-aware AQL (which we assume is handled).
            # The ArangoDB traverse method is simpler and just returns raw nodes/edges.

            logger.debug(
                f"Traversing graph starting from node: {start_node_id}")

            result = await self.graph_db.traverse(start_node_id=start_node_id,
                                                  min_depth=1,
                                                  max_depth=TRAVERSAL_DEPTH,
                                                  direction="any")

            # Merge results for all starting nodes
            full_graph_context.nodes.extend(result.nodes)
            full_graph_context.edges.extend(result.edges)

        # Filter out duplicates after merging
        unique_nodes = list({n.id: n
                             for n in full_graph_context.nodes}.values())
        unique_edges = list({e.id: e
                             for e in full_graph_context.edges}.values())

        return self._format_triples_for_llm(unique_nodes, unique_edges)

    async def _generate_answer(self, query_text: str, context: str,
                               graph_context: str,
                               query_type: QueryType) -> str:
        """Generate an answer using the LLM"""
        # Create a prompt based on the query type
        if query_type == QueryType.FACTUAL:
            prompt = self._create_factual_prompt(query_text, context,
                                                 graph_context)
        elif query_type == QueryType.RELATIONAL:
            prompt = self._create_relational_prompt(query_text, context,
                                                    graph_context)
        elif query_type == QueryType.COMPARATIVE:
            prompt = self._create_comparative_prompt(query_text, context,
                                                     graph_context)
        elif query_type == QueryType.SUMMARIZATION:
            prompt = self._create_summarization_prompt(query_text, context,
                                                       graph_context)
        elif query_type == QueryType.RECOMMENDATION:
            prompt = self._create_recommendation_prompt(
                query_text, context, graph_context)
        else:
            prompt = self._create_general_prompt(query_text, context,
                                                 graph_context)

        # Get response from LLM
        response = await self.llm.generate_response(prompt,
                                                    temperature=0.2,
                                                    max_tokens=1024)

        return response.content

    def _create_factual_prompt(self, query: str, context: str,
                               graph_context: str) -> str:
        """Create a prompt for factual queries"""
        return f"""
        You are a research assistant helping a researcher answer questions based on their research library.
        
        QUESTION: {query}
        
        RELEVANT RESEARCH PAPERS:
        {context}
        
        KNOWLEDGE GRAPH CONTEXT:
        {graph_context}
        
        Please provide a concise, factual answer to the question based on the research papers and knowledge graph.
        Include specific details and cite the relevant papers using their titles.
        If the information isn't available in the provided context, say so clearly.
        
        ANSWER:
        """

    def _create_relational_prompt(self, query: str, context: str,
                                  graph_context: str) -> str:
        """Create a prompt for relational queries"""
        return f"""
        You are a research assistant helping a researcher understand relationships between concepts.
        
        QUESTION: {query}
        
        RELEVANT RESEARCH PAPERS:
        {context}
        
        KNOWLEDGE GRAPH CONTEXT:
        {graph_context}
        
        Please explain the relationships between concepts mentioned in the question.
        Use the research papers and knowledge graph to identify how these concepts are connected.
        Include specific examples and cite the relevant papers using their titles.
        
        ANSWER:
        """

    def _create_comparative_prompt(self, query: str, context: str,
                                   graph_context: str) -> str:
        """Create a prompt for comparative queries"""
        return f"""
        You are a research assistant helping a researcher compare different approaches or concepts.
        
        QUESTION: {query}
        
        RELEVANT RESEARCH PAPERS:
        {context}
        
        KNOWLEDGE GRAPH CONTEXT:
        {graph_context}
        
        Please provide a comparison of the concepts or approaches mentioned in the question.
        Highlight similarities, differences, advantages, and disadvantages based on the research papers.
        Cite the relevant papers using their titles.
        
        ANSWER:
        """

    def _create_summarization_prompt(self, query: str, context: str,
                                     graph_context: str) -> str:
        """Create a prompt for summarization queries"""
        return f"""
        You are a research assistant helping a researcher summarize information about a topic.
        
        QUESTION: {query}
        
        RELEVANT RESEARCH PAPERS:
        {context}
        
        KNOWLEDGE GRAPH CONTEXT:
        {graph_context}
        
        Please provide a comprehensive summary of the topic based on the research papers.
        Organize the information logically and highlight key points.
        Cite the relevant papers using their titles.
        
        ANSWER:
        """

    def _create_recommendation_prompt(self, query: str, context: str,
                                      graph_context: str) -> str:
        """Create a prompt for recommendation queries"""
        return f"""
        You are a research assistant helping a researcher find relevant papers or approaches.
        
        QUESTION: {query}
        
        RELEVANT RESEARCH PAPERS:
        {context}
        
        KNOWLEDGE GRAPH CONTEXT:
        {graph_context}
        
        Please provide recommendations based on the question and the available research.
        Suggest specific papers, approaches, or next steps for the researcher.
        Explain why each recommendation is relevant and cite the papers using their titles.
        
        ANSWER:
        """

    def _create_general_prompt(self, query: str, context: str,
                               graph_context: str) -> str:
        """Create a general prompt for other query types"""
        return f"""
        You are a research assistant helping a researcher with their question.
        
        QUESTION: {query}
        
        RELEVANT RESEARCH PAPERS:
        {context}
        
        KNOWLEDGE GRAPH CONTEXT:
        {graph_context}
        
        Please provide a helpful answer to the question based on the research papers and knowledge graph.
        Be specific and cite the relevant papers using their titles.
        
        ANSWER:
        """

    async def _extract_citations(
            self, answer: str,
            relevant_papers: List[Dict[str, Any]]) -> List[Citation]:
        """Extract citations from the answer text"""
        citations = []

        for paper in relevant_papers:
            metadata = paper.get('metadata', {})
            title = metadata.get('title')

            if title and title in answer:
                citations.append(
                    Citation(paper_id=metadata.get('doc_id', ''),
                             paper_title=title,
                             authors=metadata.get('authors', []),
                             publication_date=metadata.get('publication_date'),
                             text_segment=self._extract_relevant_snippet(
                                 answer, title),
                             confidence=paper.get('score', 0.5)))

        return citations

    def _extract_relevant_snippet(self, answer: str, title: str) -> str:
        """Extract a relevant snippet of text around the citation"""
        # Find the position of the title in the answer
        pos = answer.find(title)
        if pos == -1:
            return f"Mentioned in context of: {title}"

        # Extract a snippet around the title
        start = max(0, pos - 50)
        end = min(len(answer), pos + len(title) + 50)
        return answer[start:end]

    async def _generate_follow_up_questions(self, query: str,
                                            answer: str) -> List[str]:
        """Generate suggested follow-up questions"""
        try:
            prompt = f"""
            Based on the following query and answer, suggest 3 relevant follow-up questions.
            
            QUERY: {query}
            
            ANSWER: {answer}
            
            Please return the questions as a JSON array of strings.
            
            FOLLOW-UP QUESTIONS:
            """

            response = await self.llm.generate_structured_response(
                prompt,
                response_format={"questions": ["string", "string", "string"]},
                temperature=0.3,
                max_tokens=200)

            return response.get("questions", [])

        except Exception as e:
            logger.error(f"Error generating follow-up questions: {e}")
            return []
