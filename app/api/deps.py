from fastapi import Security, HTTPException, status, Depends
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Client
from app.core.security import hash_api_key
from app.core.logger import logger
from app.core.utils import get_api_key_header_name

API_KEY_NAME = get_api_key_header_name()
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

logger.info(f"API Key Header Name: {API_KEY_NAME}")

from fastapi import Request

def get_current_client(request: Request, api_key: str = Security(api_key_header), db: Session = Depends(get_db)):
    logger.debug(f"Intercepted Raw Headers: {request.headers}")
    if not api_key:
        logger.warning(f"Unauthenticated request: API Key is missing from header (Expected: {API_KEY_NAME}).")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=f"API Key is missing from header. Expected: {API_KEY_NAME}"
        )
    
    logger.debug("Hashing API key and querying active client in DB.")
    hashed_key = hash_api_key(api_key)
    client = db.query(Client).filter(Client.api_key_hash == hashed_key, Client.is_active == True).first()
    
    if not client:
        logger.warning("Unauthenticated request: Invalid or suspended API key attempted.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or suspended API key."
        )
        
    logger.info(f"Authenticated client: {client.organization_name} (ID: {client.id})")
    return client
