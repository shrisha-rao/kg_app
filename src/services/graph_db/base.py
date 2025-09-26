# src/services/graph_db/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class Node(BaseModel):
    """Represents a node in the knowledge graph"""
    id: str
    label: str
    properties: Dict[str, Any]
    type: str  # e.g., "paper", "author", "concept", "method"


class Edge(BaseModel):
    """Represents an edge/relationship in the knowledge graph"""
    id: str
    source_id: str
    target_id: str
    label: str
    properties: Dict[str, Any]
    type: str  # e.g., "cites", "authored_by", "related_to"


class GraphQueryResult(BaseModel):
    """Result of a graph query"""
    nodes: List[Node]
    edges: List[Edge]
    execution_time: float


class GraphDBService(ABC):
    """Abstract base class for graph database services"""

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the graph database"""
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the graph database"""
        pass

    @abstractmethod
    async def upsert_node(self, node: Node) -> bool:
        """Insert or update a node in the graph"""
        pass

    @abstractmethod
    async def upsert_edge(self, edge: Edge) -> bool:
        """Insert or update an edge in the graph"""
        pass

    @abstractmethod
    async def get_node(self, node_id: str) -> Optional[Node]:
        """Get a node by ID"""
        pass

    @abstractmethod
    async def get_edge(self, edge_id: str) -> Optional[Edge]:
        """Get an edge by ID"""
        pass

    @abstractmethod
    async def query_nodes(self,
                          label: Optional[str] = None,
                          properties: Optional[Dict[str, Any]] = None,
                          limit: int = 100) -> List[Node]:
        """Query nodes by label and/or properties"""
        pass

    @abstractmethod
    async def query_edges(self,
                          label: Optional[str] = None,
                          properties: Optional[Dict[str, Any]] = None,
                          limit: int = 100) -> List[Edge]:
        """Query edges by label and/or properties"""
        pass

    @abstractmethod
    async def traverse(
            self,
            start_node_id: str,
            min_depth: int = 1,
            max_depth: int = 3,
            direction: str = "any",
            edge_labels: Optional[List[str]] = None) -> GraphQueryResult:
        """Traverse the graph from a starting node"""
        pass

    @abstractmethod
    async def delete_node(self, node_id: str) -> bool:
        """Delete a node and its edges"""
        pass

    @abstractmethod
    async def delete_edge(self, edge_id: str) -> bool:
        """Delete an edge"""
        pass

    @abstractmethod
    async def execute_query(
            self,
            query: str,
            params: Optional[Dict[str, Any]] = None) -> GraphQueryResult:
        """Execute a custom query in the database's query language"""
        pass
