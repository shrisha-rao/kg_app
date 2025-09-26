# src/api/query.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from src.services.query_processing import QueryProcessingService

router = APIRouter()


class QueryRequest(BaseModel):
    question: str
    user_id: str
    use_public_data: bool = True
    use_private_data: bool = True


@router.post("/query")
async def query_knowledge_graph(request: QueryRequest):
    try:
        processor = QueryProcessingService()
        result = await processor.process_query(
            user_id=request.user_id,
            question=request.question,
            use_public_data=request.use_public_data,
            use_private_data=request.use_private_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
