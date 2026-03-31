from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool
import time
import uuid
import secrets

from app.core.config import settings
from app.core.logger import logger
from app.core.security import hash_api_key
from app.db.database import get_db
from app.db.models import Client, VerificationLog, ErrorTelemetry
from app.schemas.payload import VerificationResult, APIResponse, ClientCreate, ClientResponse
from app.api.deps import get_current_client
from app.core.utils import validate_image
from app.services.ai_service import verify_signatures

router = APIRouter()

def _log_transaction(db: Session, client_id: int, transaction_ref: str, score: float, verdict: str, processing_time_ms: int, fallback_exception: Exception):
    try:
        db_log = VerificationLog(
            client_id=client_id,
            transaction_reference=transaction_ref,
            score=score,
            verdict=verdict,
            processing_time_ms=processing_time_ms,
            http_status_code=200
        )
        db.add(db_log)
        db.flush()
        
        if fallback_exception:
            telemetry = ErrorTelemetry(
                log_id=db_log.id,
                provider_used=settings.PRIMARY_LLM_PROVIDER,
                error_type=type(fallback_exception).__name__,
                stack_trace=str(fallback_exception)
            )
            db.add(telemetry)
            
        db.commit()
    except SQLAlchemyError as db_err:
        db.rollback()
        logger.error(f"Non-fatal Database Error for ref {transaction_ref}: {str(db_err)}. Proceeding with payload delivery.")

@router.post("/verify", response_model=APIResponse, status_code=status.HTTP_200_OK)
async def verify_signature_endpoint(
    genuine_image: UploadFile = File(...),
    questioned_image: UploadFile = File(...),
    current_client: Client = Depends(get_current_client),
    db: Session = Depends(get_db)
):
    start_time = time.time()
    transaction_ref = str(uuid.uuid4())
    logger.info(f"Verification requested by {current_client.organization_name} | Ref: {transaction_ref}")
    
    validate_image(genuine_image)
    validate_image(questioned_image)
    
    try:
        verification_result, provider_used, fallback_exception = await verify_signatures(
            genuine_image, questioned_image
        )
    except Exception as e:
        logger.error(f"Fatal verification error for ref {transaction_ref}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal AI Processing Error. Support has been notified."
        )
        
    processing_time_ms = int((time.time() - start_time) * 1000)
    
    await run_in_threadpool(
        _log_transaction,
        db, current_client.id, transaction_ref,
        verification_result.score, verification_result.verdict, 
        processing_time_ms, fallback_exception
    )
        
    logger.info(f"Complete | Ref: {transaction_ref} | Time: {processing_time_ms}ms | Provider: {provider_used}")
    
    return APIResponse(
        transaction_reference=transaction_ref,
        processing_time_ms=processing_time_ms,
        result=verification_result
    )

@router.post("/internal/clients", response_model=ClientResponse, tags=["Admin"])
def create_client(client_in: ClientCreate, db: Session = Depends(get_db)):
    """Create a new client with a raw API key"""
    raw_api_key = secrets.token_urlsafe(32)
    hashed_key = hash_api_key(raw_api_key)
    
    db_client = Client(
        api_key_hash=hashed_key,
        organization_name=client_in.organization_name,
        tier=client_in.tier
    )
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    
    return ClientResponse(
        id=db_client.id,
        organization_name=db_client.organization_name,
        tier=db_client.tier,
        is_active=db_client.is_active,
        api_key=raw_api_key  # Send ONCE
    )
