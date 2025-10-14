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

# logging.basicConfig(level=logging.DEBUG)
# # or for uvicorn:
# logging.getLogger("uvicorn").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
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

            logger.info("step 1: Generating query embedding")

            # Step 1: Generate query embedding
            query_embedding = await self._generate_query_embedding(
                query.query_text)

            logger.info("step 2: Search for relevant papers in vector DB")

            # Step 2: Search for relevant papers in vector DB
            relevant_papers = await self._search_relevant_papers(
                query_embedding, query.scope, query.user_id, top_k=10)

            logger.info("step 3: Extract context from relevant papers")
            # Step 3: Extract context from relevant papers
            context = await self._build_context(relevant_papers,
                                                query.query_text)

            logger.info(
                "Step 4: Query the knowledge graph for related entities")
            # Step 4: Query the knowledge graph for related entities
            logger.info(f"Step 4a: query_text: {query.query_text}")
            logger.info(f"Step 4b: query scope: {query.scope}")
            logger.info(f"Step 4c: query user_id: {query.user_id}")
            logger.info(f"Step 4d: query type: {query.query_type}")
            graph_context = await self._query_knowledge_graph(
                query.query_text, query.scope, query.user_id)

            logger.info(f"Step 4e: graph_context: {graph_context}")

            logger.info("Step 5: Generate answer using LLM")
            # Step 5: Generate answer using LLM
            answer = await self._generate_answer(query.query_text, context,
                                                 graph_context,
                                                 query.query_type)

            logger.info("Step 6: Extract citations from the answer")
            # Step 6: Extract citations from the answer
            citations = await self._extract_citations(answer, relevant_papers)

            logger.info("Step 7: Create response")
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
            filter={"is_public": [True,
                                  False]}  # Get both public and private papers
        )
        results.extend(user_results)

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

    async def _query_knowledge_graph(self, query_text: str, scope: QueryScope,
                                     user_id: str) -> str:
        """Query the knowledge graph for entities and relationships related to the query"""
        try:
            # FIX: Add a safety check for uninitialized graph DB
            if self.graph_db is None:
                logger.warning("Knowledge Graph service is not initialized.")
                return "Knowledge Graph service is unavailable or failed to initialize."

            # Extract key entities from the query
            entities = await self._extract_entities_from_query(query_text)

            if not entities:
                return "No relevant entities found in the knowledge graph."

            # Query the graph for each entity
            graph_context_parts = []
            for entity in entities[:3]:  # Limit to top 3 entities
                # Search for nodes matching this entity
                nodes = await self.graph_db.query_nodes(
                    properties={"original_text": entity}, limit=5)
                # nodes = await self.graph_db.query_nodes(
                #     properties={"text": entity}, limit=5)

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
