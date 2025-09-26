# src/models/paper.py
from datetime import datetime
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, validator
import re

# Import from your existing user model
from .user import User


class Entity(BaseModel):
    text: str
    type: Literal["person", "organization", "location", "concept",
                  "methodology"]
    confidence: float = Field(ge=0.0, le=1.0)
    entity_id: Optional[str] = None  # For graph database reference


class Relation(BaseModel):
    source_entity: Entity
    target_entity: Entity
    relationship: str
    confidence: float = Field(ge=0.0, le=1.0)
    relation_id: Optional[str] = None  # For graph database reference


class PaperBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    authors: List[str] = Field(default_factory=list)
    publication_date: Optional[datetime] = None
    journal_or_conference: Optional[str] = Field(None, max_length=200)
    doi: Optional[str] = None
    abstract: Optional[str] = Field(None, max_length=5000)

    @validator('doi')
    def validate_doi_format(cls, v):
        if v is None:
            return v
        # Basic DOI format validation
        doi_pattern = r'^10\.\d{4,9}/[-._;()/:A-Z0-9]+$'
        if not re.match(doi_pattern, v, re.IGNORECASE):
            raise ValueError('Invalid DOI format')
        return v


class PaperCreate(PaperBase):
    raw_text_path: str = Field(..., description="GCS path to extracted text")
    pdf_storage_path: str = Field(..., description="GCS path to original PDF")
    file_hash: str = Field(...,
                           min_length=32,
                           max_length=64,
                           description="File hash for duplicate detection")
    owner_id: str = Field(..., description="Firebase UID of the owner")

    @validator('raw_text_path', 'pdf_storage_path')
    def validate_gcs_path_format(cls, v):
        # Basic GCS path validation
        if not (v.startswith('gs://') or v.startswith('users/')
                or v.startswith('/')):
            # raise ValueError('GCS paths must start with gs://')
            raise ValueError("Paths must start with 'gs://', 'users/', or '/'")
        return v


class PaperUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    authors: Optional[List[str]] = None
    journal_or_conference: Optional[str] = Field(None, max_length=200)
    doi: Optional[str] = None
    abstract: Optional[str] = Field(None, max_length=5000)
    visibility: Optional[Literal["private", "shared", "public"]] = None
    collaborators: Optional[List[str]] = None

    @validator('doi')
    def validate_doi_format(cls, v):
        if v is None:
            return v
        doi_pattern = r'^10\.\d{4,9}/[-._;()/:A-Z0-9]+$'
        if not re.match(doi_pattern, v, re.IGNORECASE):
            raise ValueError('Invalid DOI format')
        return v


class PaperInDB(PaperBase):
    id: str = Field(..., description="Firestore document ID")
    raw_text_path: str
    pdf_storage_path: str
    file_hash: str
    processing_status: Literal["pending", "processing", "completed",
                               "failed"] = "pending"
    embedding_status: Literal["pending", "completed", "failed"] = "pending"
    graph_status: Literal["pending", "completed", "failed"] = "pending"
    visibility: Literal["private", "shared", "public"] = "private"
    owner_id: str
    collaborators: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    entities: List[Entity] = Field(default_factory=list)
    relations: List[Relation] = Field(default_factory=list)
    embedding_id: Optional[str] = Field(
        None, description="Reference to embedding in vector database")
    graph_node_id: Optional[str] = Field(
        None, description="Reference to node in graph database")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class Paper(PaperInDB):
    owner: Optional[User] = None
    shared_with: Optional[List[User]] = None


class PaperResponse(BaseModel):
    """Simplified model for API responses"""
    id: str
    title: str
    authors: List[str]
    publication_date: Optional[datetime]
    journal_or_conference: Optional[str]
    doi: Optional[str]
    abstract: Optional[str]
    visibility: Literal["private", "shared", "public"]
    owner_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class PaperListResponse(BaseModel):
    """Response model for listing papers"""
    papers: List[PaperResponse]
    total_count: int
    page: int
    page_size: int


class PaperUploadResponse(BaseModel):
    """Response model for paper upload"""
    paper_id: str
    status: Literal["accepted", "duplicate", "error"]
    message: Optional[str] = None
