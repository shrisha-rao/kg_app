# src/models/query.py
from datetime import datetime
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class QueryType(str, Enum):
    """Types of queries supported by the system"""
    FACTUAL = "factual"  # Specific facts or information
    RELATIONAL = "relational"  # Relationships between concepts
    COMPARATIVE = "comparative"  # Comparison between papers/concepts
    SUMMARIZATION = "summarization"  # Summary of content
    RECOMMENDATION = "recommendation"  # Paper recommendations


class QueryScope(str, Enum):
    """Scope of the query"""
    PERSONAL = "personal"  # Only user's private papers
    SHARED = "shared"  # User's papers plus shared papers
    PUBLIC = "public"  # All public papers
    CROSS_DOMAIN = "cross_domain"  # Across multiple knowledge domains


class Citation(BaseModel):
    """Citation to a specific paper or text segment"""
    paper_id: str
    paper_title: str
    authors: List[str]
    publication_date: Optional[datetime] = None
    page_number: Optional[int] = None
    text_segment: str
    confidence: float = Field(ge=0.0, le=1.0)


class QueryBase(BaseModel):
    query_text: str = Field(...,
                            min_length=1,
                            max_length=1000,
                            description="The natural language query")
    query_type: QueryType = Field(QueryType.FACTUAL,
                                  description="Type of query")
    scope: QueryScope = Field(QueryScope.PERSONAL,
                              description="Scope of the search")


class QueryCreate(QueryBase):
    user_id: str = Field(..., description="ID of the user making the query")


class QueryInDB(QueryBase):
    id: str = Field(..., description="Unique identifier for the query")
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processing_time: Optional[float] = Field(
        None, description="Time taken to process the query in seconds")
    status: Literal["pending", "processing", "completed", "failed"] = "pending"
    llm_model: Optional[str] = Field(
        None, description="LLM model used for processing")
    vector_search_results: Optional[List[str]] = Field(
        None, description="IDs of papers from vector search")
    graph_search_results: Optional[List[str]] = Field(
        None, description="IDs of papers from graph search")

    class Config:
        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class QueryResponse(BaseModel):
    """Response to a query"""
    query_id: str
    answer: str = Field(..., description="The generated answer to the query")
    citations: List[Citation] = Field(
        default_factory=list, description="Citations supporting the answer")
    confidence: float = Field(ge=0.0,
                              le=1.0,
                              description="Confidence score of the answer")
    suggested_follow_up_questions: List[str] = Field(
        default_factory=list, description="Suggested follow-up questions")
    processed_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class QueryWithResponse(QueryInDB):
    """Query along with its response"""
    response: Optional[QueryResponse] = None


class QueryHistoryResponse(BaseModel):
    """Response model for query history"""
    queries: List[QueryWithResponse]
    total_count: int
    page: int
    page_size: int


class QueryAnalysis(BaseModel):
    """Analysis of a query for optimization"""
    query_id: str
    tokens_used: Optional[int] = Field(
        None, description="Number of tokens used in processing")
    cost_estimate: Optional[float] = Field(
        None, description="Estimated cost of processing")
    performance_metrics: Dict[str,
                              float] = Field(default_factory=dict,
                                             description="Performance metrics")


class QueryFeedback(BaseModel):
    """User feedback on a query response"""
    query_id: str
    user_id: str
    rating: int = Field(ge=1, le=5, description="Rating from 1 to 5")
    helpful: bool = Field(True, description="Whether the response was helpful")
    comments: Optional[str] = Field(None,
                                    max_length=500,
                                    description="Additional comments")
    corrected_answer: Optional[str] = Field(
        None,
        max_length=2000,
        description="User's corrected answer if applicable")


class QueryStats(BaseModel):
    """Statistics about queries"""
    total_queries: int
    average_processing_time: float
    success_rate: float
    most_common_query_types: Dict[QueryType, int]
    most_active_users: Dict[str, int]  # user_id -> query_count
