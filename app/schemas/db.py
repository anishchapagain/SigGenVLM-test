from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class BaseSchema(BaseModel):
    """
    Base generic schema enabling automatic serialization 
    from underlying SQLAlchemy Models directly into JSON Responses.
    """
    model_config = ConfigDict(from_attributes=True)
    id: int

class AdminUserDB(BaseSchema):
    username: str
    role: str
    created_at: datetime

class ClientDB(BaseSchema):
    organization_name: str
    tier: str
    is_active: bool
    created_at: datetime

class VerificationLogDB(BaseSchema):
    client_id: int
    transaction_reference: str
    score: float
    verdict: str
    human_reviewed_verdict: Optional[str] = None
    processing_time_ms: int
    http_status_code: int
    timestamp: datetime

class ErrorTelemetryDB(BaseSchema):
    log_id: Optional[int] = None
    provider_used: str
    error_type: str
    stack_trace: str
    timestamp: datetime
