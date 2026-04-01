from fastapi import UploadFile, HTTPException, status
from app.core.config import settings
from app.core.logger import logger

def get_api_key_header_name() -> str:
    provider = settings.PRIMARY_LLM_PROVIDER
    if provider:
        logger.debug(f"API key header name mapped for provider {provider}: {provider.upper()}-API-KEY")
        return f"{provider.upper()}-API-KEY"
    logger.warning("No API key header name found.")
    return "X-API-KEY"

def validate_image(file: UploadFile):
    """
    Validates uploaded image byte size and content type securely.
    """
    logger.debug(f"Validating constraints for uploaded image: {file.filename}")
    try:
        if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
            logger.error(f"Validation failed: Invalid content type '{file.content_type}' for {file.filename}.")
            raise ValueError(f"Invalid file type: {file.content_type}. Allowed: {settings.ALLOWED_IMAGE_TYPES}")
            
        file.file.seek(0, 2)
        file_size_kb = file.file.tell() / 1024
        file.file.seek(0)
        
        if file_size_kb < settings.MIN_IMAGE_SIZE_KB:
            logger.error(f"Validation failed: Image {file.filename} is too small ({file_size_kb}KB).")
            raise ValueError(f"Image {file.filename} is too small. Minimum size is {settings.MIN_IMAGE_SIZE_KB}KB.")
            
        if file_size_kb > (settings.MAX_IMAGE_SIZE_MB * 1024):
            logger.error(f"Validation failed: Image {file.filename} is too large ({file_size_kb}KB).")
            raise ValueError(f"Image {file.filename} is too large. Maximum size is {settings.MAX_IMAGE_SIZE_MB}MB.")
            
        logger.debug(f"Validation passed for {file.filename} ({file_size_kb:.2f}KB).")
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Validation exception for {file.filename}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded file stream is corrupted or unreadable: {str(e)}"
        )
