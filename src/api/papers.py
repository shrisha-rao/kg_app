#src/api/papers.py
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from typing import List, Optional
from src.utils.auth import get_current_user
from src.services.file_processing import FileProcessingService
from src.models.user import UserResponse

router = APIRouter(prefix="/papers", tags=["papers"])


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_paper(file: UploadFile = File(...),
                       is_public: bool = Form(False),
                       current_user: dict = Depends(get_current_user)):
    """
    Upload a research paper (protected endpoint)
    """
    try:
        content = await file.read()
        processor = FileProcessingService()
        result = await processor.process_uploaded_file(
            user_id=current_user["uid"],
            file_content=content,
            filename=file.filename,
            is_public=is_public)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/", response_model=List[dict])
async def get_papers(current_user: dict = Depends(get_current_user)):
    """
    Get user's papers (protected endpoint)
    """
    # Implementation to get user's papers from database
    pass
