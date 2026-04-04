"""
Signature Forensic Analysis API
FastAPI implementation with OpenAI GPT-4o Vision

This API performs forensic signature verification using AI-powered analysis.
Returns structured JSON with verdict, confidence score, and detailed characteristics.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Tuple, Dict, Any, Optional
from pydantic import BaseModel
import base64
import json
import os
import time
from datetime import datetime
from openai import OpenAI

# -----------------------------
# App Configuration
# -----------------------------

app = FastAPI(
    title="Signature Forensic Analysis API",
    description="AI-powered signature verification using forensic document examination principles",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware (configure as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Configuration
DEFAULT_MODEL = "gpt-4o"  # Options: gpt-4o, gpt-4-turbo, gpt-4o-mini
TEMPERATURE = 0.2
MAX_TOKENS = 2048

# -----------------------------
# System Prompt (Forensic Expert)
# -----------------------------

FORENSIC_SYSTEM_PROMPT = """You are an expert forensic document examiner with over 20 years of experience in signature analysis and handwriting verification. Your role is to analyze signatures with the precision and methodology used in legal and investigative contexts.

Your expertise includes:
- Microscopic examination of stroke patterns and pen pressure
- Detection of forgery indicators such as tremor, hesitation, and unnatural pen lifts
- Analysis of writing dynamics including speed, rhythm, and fluidity
- Identification of unique biometric characteristics in handwriting
- Comparison of structural elements: slant, spacing, proportion, and baseline alignment
- Recognition of simulation techniques vs. natural variation

When analyzing signatures, you evaluate:
1. **Structural Consistency**: Overall shape, letter formation, size ratios, slant angle
2. **Dynamic Features**: Writing speed, pen pressure variation, stroke confidence
3. **Natural Flow**: Smooth connections, consistent rhythm, habitual patterns
4. **Terminal Strokes**: Entry and exit points, tapers, flourishes
5. **Unique Identifiers**: Personal characteristics, distinctive loops, crossing patterns
6. **Forgery Indicators**: Tremor, hesitation marks, pen lifts, retouching, tracing signs

Your analysis must be objective, methodical, and based on established forensic principles. You provide verdicts with confidence scores and detailed supporting characteristics."""

# -----------------------------
# Pydantic Models
# -----------------------------

class SignatureAnalysisResult(BaseModel):
    """Result model for signature analysis"""
    verdict: str
    score: int
    characteristics: list[str]

class UsageMetrics(BaseModel):
    """Usage metrics for API call"""
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    latency_sec: float
    model: str

class AnalysisResponse(BaseModel):
    """Complete response model"""
    result: SignatureAnalysisResult
    usage: UsageMetrics
    timestamp: str
    api_version: str = "2.0.0"

# -----------------------------
# Utility Functions
# -----------------------------

def validate_image_bytes(file_bytes: bytes) -> str:
    """
    Validates image format based on magic numbers.
    Supports: PNG, JPG, JPEG
    Returns detected MIME type.
    """
    # PNG magic number: 89 50 4E 47 0D 0A 1A 0A
    if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"

    # JPEG magic number: FF D8 FF
    if file_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    
    # Also accept JPEG files that start with just FF D8
    if file_bytes.startswith(b"\xff\xd8"):
        return "image/jpeg"

    raise ValueError(
        "Unsupported image format. Please upload PNG or JPEG images only."
    )


def encode_to_data_url(file_bytes: bytes, mime_type: str) -> str:
    """
    Encodes image bytes to base64 data URL.
    
    Args:
        file_bytes: Raw image bytes
        mime_type: MIME type (image/png or image/jpeg)
    
    Returns:
        Base64-encoded data URL
    """
    b64 = base64.b64encode(file_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"


def build_analysis_prompt() -> str:
    """
    Builds the user prompt for forensic signature analysis.
    Instructs the model to return structured JSON.
    """
    return """Compare these two signatures as a forensic document examiner.

The FIRST image is the REFERENCE signature (known authentic sample).
The SECOND image is the QUESTIONED signature (to be verified).

Perform a comprehensive forensic analysis and provide your findings in VALID JSON format ONLY. Do not include any markdown formatting, code blocks, or explanatory text outside the JSON.

Your response must be a single JSON object with this exact structure:

{
  "verdict": "Genuine" or "Forged" or "Inconclusive",
  "score": <confidence score 0-100>,
  "characteristics": [
    "<characteristic 1: detailed observation>",
    "<characteristic 2: detailed observation>",
    "<characteristic 3: detailed observation>",
    "<characteristic 4: detailed observation>",
    "<characteristic 5: detailed observation>"
  ]
}

Guidelines for your analysis:

**VERDICT:**
- "Genuine": Strong evidence both signatures are from the same person
- "Forged": Clear evidence of forgery, simulation, or different writer
- "Inconclusive": Insufficient distinctive features or conflicting evidence

**SCORE (0-100):**
- 90-100: Extremely high confidence, overwhelming evidence
- 75-89: High confidence, strong supporting evidence
- 60-74: Moderate confidence, some supporting evidence
- 40-59: Low confidence, mixed or weak evidence
- 0-39: Very low confidence, contradictory evidence

**CHARACTERISTICS (5-7 observations):**
Provide specific, technical observations about:
1. Structural alignment and proportions
2. Writing flow and naturalness
3. Terminal strokes and endpoints
4. Height/width ratios and consistency
5. Pressure patterns and line quality
6. Unique identifiers or forgery indicators
7. Overall writing dynamics

Each characteristic should be a complete sentence describing a specific forensic finding.

CRITICAL: Return ONLY the JSON object. No additional text, no markdown code blocks, no explanations."""


# -----------------------------
# OpenAI API Call
# -----------------------------

def call_openai_vision(
    image1_url: str, 
    image2_url: str,
    model: str = DEFAULT_MODEL
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Calls OpenAI Vision API for signature analysis.
    
    Args:
        image1_url: Base64 data URL of reference signature
        image2_url: Base64 data URL of questioned signature
        model: OpenAI model to use
    
    Returns:
        Tuple of (analysis_result, usage_metrics)
    """
    start_time = time.time()

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": FORENSIC_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": build_analysis_prompt()
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image1_url
                            }
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image2_url
                            }
                        }
                    ]
                }
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS
        )

        latency = round(time.time() - start_time, 3)

        # Extract response text
        response_text = response.choices[0].message.content
        
        # Clean up response - remove markdown code blocks if present
        cleaned_response = response_text.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        cleaned_response = cleaned_response.strip()

        # Parse JSON
        try:
            result = json.loads(cleaned_response)
        except json.JSONDecodeError as je:
            raise ValueError(f"Failed to parse JSON response: {je}\nRaw response: {response_text}")

        # Build usage metrics
        usage = {
            "input_tokens": response.usage.prompt_tokens if response.usage else None,
            "output_tokens": response.usage.completion_tokens if response.usage else None,
            "total_tokens": response.usage.total_tokens if response.usage else None,
            "latency_sec": latency,
            "model": model,
        }

        return result, usage

    except Exception as e:
        raise Exception(f"OpenAI API error: {str(e)}")


# -----------------------------
# Logging Layer
# -----------------------------

def log_analysis(data: Dict[str, Any]):
    """
    Logs analysis data to JSONL file.
    In production, replace with database (PostgreSQL, MongoDB, etc.)
    
    Args:
        data: Dictionary containing analysis metadata
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        **data,
    }

    try:
        with open("forensic_analysis_logs.jsonl", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"Logging error: {e}")


# -----------------------------
# API Endpoints
# -----------------------------

@app.get("/")
def root():
    """Root endpoint - API health check"""
    return {
        "status": "running",
        "service": "Signature Forensic Analysis API",
        "version": "2.0.0",
        "model": DEFAULT_MODEL,
        "endpoints": {
            "verify": "/verify-signature",
            "docs": "/docs",
            "health": "/health"
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    openai_configured = bool(os.getenv("OPENAI_API_KEY"))
    
    return {
        "status": "healthy" if openai_configured else "degraded",
        "timestamp": datetime.now().isoformat(),
        "openai_configured": openai_configured,
        "model": DEFAULT_MODEL
    }


@app.post("/verify-signature", response_model=AnalysisResponse)
async def verify_signature(
    request: Request,
    reference_signature: UploadFile = File(..., description="Reference signature (known authentic)"),
    questioned_signature: UploadFile = File(..., description="Questioned signature (to be verified)"),
    model: Optional[str] = None
):
    """
    Verify signature authenticity using forensic analysis.
    
    Args:
        reference_signature: Reference signature image (PNG/JPEG)
        questioned_signature: Questioned signature image (PNG/JPEG)
        model: Optional model override (gpt-4o, gpt-4-turbo, gpt-4o-mini)
    
    Returns:
        AnalysisResponse with verdict, score, characteristics, and usage metrics
    
    Raises:
        HTTPException: For invalid inputs or API errors
    """
    try:
        # Validate API key
        if not os.getenv("OPENAI_API_KEY"):
            raise HTTPException(
                status_code=503,
                detail="OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
            )

        # Read uploaded files
        ref_bytes = await reference_signature.read()
        quest_bytes = await questioned_signature.read()

        # Validate image formats
        ref_mime = validate_image_bytes(ref_bytes)
        quest_mime = validate_image_bytes(quest_bytes)

        # Encode to data URLs
        ref_data_url = encode_to_data_url(ref_bytes, ref_mime)
        quest_data_url = encode_to_data_url(quest_bytes, quest_mime)

        # Use specified model or default
        analysis_model = model if model in ["gpt-4o", "gpt-4-turbo", "gpt-4o-mini"] else DEFAULT_MODEL

        # Call OpenAI API
        result, usage = call_openai_vision(ref_data_url, quest_data_url, analysis_model)

        # Validate result structure
        if "verdict" not in result or "score" not in result or "characteristics" not in result:
            raise ValueError("Invalid response structure from AI model")

        # Log the analysis
        log_analysis({
            "client_ip": request.client.host,
            "endpoint": "/verify-signature",
            "model": analysis_model,
            "verdict": result.get("verdict"),
            "score": result.get("score"),
            "usage": usage,
            "reference_filename": reference_signature.filename,
            "questioned_filename": questioned_signature.filename,
        })

        # Return structured response
        return AnalysisResponse(
            result=SignatureAnalysisResult(**result),
            usage=UsageMetrics(**usage),
            timestamp=datetime.now().isoformat()
        )

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    
    except Exception as e:
        # Log error
        log_analysis({
            "client_ip": request.client.host,
            "endpoint": "/verify-signature",
            "error": str(e),
            "status": "failed"
        })
        
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/verify-signature-batch")
async def verify_signature_batch(
    request: Request,
    files: list[UploadFile] = File(..., description="List of signature pairs (even indices are reference, odd are questioned)")
):
    """
    Batch signature verification endpoint.
    Upload pairs of signatures for bulk analysis.
    
    Args:
        files: List of images where files[0], files[2], files[4]... are reference signatures
               and files[1], files[3], files[5]... are questioned signatures
    
    Returns:
        List of analysis results
    """
    if len(files) % 2 != 0:
        raise HTTPException(
            status_code=400,
            detail="Must upload an even number of files (pairs of reference and questioned signatures)"
        )
    
    results = []
    
    for i in range(0, len(files), 2):
        try:
            ref_file = files[i]
            quest_file = files[i + 1]
            
            ref_bytes = await ref_file.read()
            quest_bytes = await quest_file.read()
            
            ref_mime = validate_image_bytes(ref_bytes)
            quest_mime = validate_image_bytes(quest_bytes)
            
            ref_data_url = encode_to_data_url(ref_bytes, ref_mime)
            quest_data_url = encode_to_data_url(quest_bytes, quest_mime)
            
            result, usage = call_openai_vision(ref_data_url, quest_data_url)
            
            results.append({
                "pair_index": i // 2,
                "reference_file": ref_file.filename,
                "questioned_file": quest_file.filename,
                "result": result,
                "usage": usage,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            results.append({
                "pair_index": i // 2,
                "reference_file": files[i].filename,
                "questioned_file": files[i + 1].filename,
                "error": str(e),
                "status": "failed"
            })
    
    return {"total_pairs": len(results), "results": results}


# -----------------------------
# Error Handlers
# -----------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat()
        }
    )


# -----------------------------
# Startup Event
# -----------------------------

@app.on_event("startup")
async def startup_event():
    """Startup tasks"""
    print("=" * 80)
    print("Signature Forensic Analysis API")
    print("=" * 80)
    print(f"Model: {DEFAULT_MODEL}")
    print(f"Temperature: {TEMPERATURE}")
    print(f"Max Tokens: {MAX_TOKENS}")
    print(f"OpenAI API Key: {'✓ Configured' if os.getenv('OPENAI_API_KEY') else '✗ Not configured'}")
    print("=" * 80)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)