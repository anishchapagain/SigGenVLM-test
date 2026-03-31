from fastapi import Security, HTTPException, status, Depends
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Client
from app.core.security import hash_api_key

API_KEY_NAME = "x-api-key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def get_current_client(api_key: str = Security(api_key_header), db: Session = Depends(get_db)):
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="API Key is missing."
        )
    
    hashed_key = hash_api_key(api_key)
    client = db.query(Client).filter(Client.api_key_hash == hashed_key, Client.is_active == True).first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or suspended API key."
        )
        
    return client
