from fastapi import UploadFile, HTTPException, status
from app.core.config import settings

def validate_image(file: UploadFile):
    """
    Validates uploaded image byte size and content type securely.
    """
    try:
        if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
            raise ValueError(f"Invalid file type: {file.content_type}. Allowed: {settings.ALLOWED_IMAGE_TYPES}")
            
        file.file.seek(0, 2)
        file_size_kb = file.file.tell() / 1024
        file.file.seek(0)
        
        if file_size_kb < settings.MIN_IMAGE_SIZE_KB:
            raise ValueError(f"Image {file.filename} is too small. Minimum size is {settings.MIN_IMAGE_SIZE_KB}KB.")
            
        if file_size_kb > (settings.MAX_IMAGE_SIZE_MB * 1024):
            raise ValueError(f"Image {file.filename} is too large. Maximum size is {settings.MAX_IMAGE_SIZE_MB}MB.")
            
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded file stream is corrupted or unreadable: {str(e)}"
        )
