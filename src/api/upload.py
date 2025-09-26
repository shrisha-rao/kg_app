# # src/api/upload.py
# from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
# from typing import Optional
# from src.services.file_processing import FileProcessingService

# router = APIRouter()

# @router.post("/upload")
# async def upload_file(
#         file: UploadFile = File(...),
#         is_public: bool = Form(False),
#         user_id: str = Form(...)  # In production, use proper authentication
# ):
#     if not file.filename.endswith('.pdf'):
#         raise HTTPException(status_code=400,
#                             detail="Only PDF files are supported")

#     try:
#         content = await file.read()
#         processor = FileProcessingService()
#         result = await processor.process_uploaded_file(user_id=user_id,
#                                                        file_content=content,
#                                                        filename=file.filename,
#                                                        is_public=is_public)
#         return result
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# src/api/upload.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import Optional
from src.services.file_processing import FileProcessingService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload")
async def upload_file(file: UploadFile = File(...),
                      is_public: bool = Form(False),
                      user_id: str = Form(...)):
    logger.info(
        f"Received upload request: {file.filename}, size: {file.size}, user: {user_id}"
    )

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400,
                            detail="Only PDF files are supported")

    try:
        # Read the file content
        content = await file.read()
        logger.info(f"Read {len(content)} bytes from file")

        if len(content) == 0:
            raise HTTPException(status_code=400,
                                detail="Uploaded file is empty")

        processor = FileProcessingService()
        result = await processor.process_uploaded_file(
            user_id=user_id,
            file_content=content,  # Pass bytes, not file path
            filename=file.filename,
            is_public=is_public)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500,
                            detail=f"Error processing file: {str(e)}")
