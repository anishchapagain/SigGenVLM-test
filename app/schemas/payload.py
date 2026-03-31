from pydantic import BaseModel, Field, ConfigDict
from typing import List

class VerificationResult(BaseModel):
    verdict: str = Field(..., description="Must be 'Genuine' or 'Forgery'")
    score: float = Field(..., description="Similarity score between 0 and 100")
    characteristics: List[str] = Field(..., description="List of observed characteristics")

class ClientCreate(BaseModel):
    organization_name: str
    tier: str = "standard"

class ClientResponse(BaseModel):
    id: int
    organization_name: str
    tier: str
    is_active: bool
    api_key: str

    model_config = ConfigDict(from_attributes=True)

class APIResponse(BaseModel):
    transaction_reference: str
    processing_time_ms: int
    result: VerificationResult
