"""
Signature Forensic Analysis API
FastAPI implementation with Multi-Provider VLM Support (OpenAI, Gemini, Groq, Ollama)

This API performs forensic signature verification using AI-powered Vision Language Models.
Returns structured JSON with verdict, confidence score, and detailed characteristics.

Run: uvicorn main:app --reload
"""

# Load .env FIRST — before any library reads environment variables
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Tuple, Dict, Any, Optional, List
import base64
import json
import os
import time
import re
from datetime import datetime

# -----------------------------
# Load Settings
# -----------------------------
# Import the project's settings object (reads from .env automatically)
from app.core.config import settings
from app.core.utils import get_provider, get_models

# -----------------------------
# Provider Client Imports
# -----------------------------
try:
    from openai import OpenAI
    localllm_available = True
except ImportError:
    localllm_available = False

try:
    from google import genai as google_genai
    _gemini_available = True
except ImportError:
    _gemini_available = False

try:
    from groq import Groq
    _groq_available = True
except ImportError:
    _groq_available = False

try:
    import ollama as ollama_client
    _ollama_available = True
except ImportError:
    _ollama_available = False

# -----------------------------
# App Initialization
# -----------------------------

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    provider=get_provider(),
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Forensic System Prompt
# -----------------------------

FORENSIC_SYSTEM_PROMPT = """You are an expert forensic document examiner with over 20 years of experience \
in signature analysis and handwriting verification. Your role is to analyze signatures with the precision \
and methodology used in legal and investigative contexts.

Your expertise includes:
- Microscopic examination of stroke patterns and pen pressure
- Detection of forgery indicators such as tremor, hesitation, and unnatural pen lifts
- Analysis of writing dynamics including speed, rhythm, and fluidity
- Identification of unique biometric characteristics in handwriting
- Comparison of structural elements: slant, spacing, proportion, and baseline alignment
- Recognition of simulation techniques vs. natural variation

When analyzing signatures, you evaluate:
1. Structural Consistency: Overall shape, letter formation, size ratios, slant angle
2. Dynamic Features: Writing speed, pen pressure variation, stroke confidence
3. Natural Flow: Smooth connections, consistent rhythm, habitual patterns
4. Terminal Strokes: Entry and exit points, tapers, flourishes
5. Unique Identifiers: Personal characteristics, distinctive loops, crossing patterns
6. Forgery Indicators: Tremor, hesitation marks, pen lifts, retouching, tracing signs

Your analysis must be objective, methodical, and based on established forensic principles."""

# -----------------------------
# Pydantic Response Models
# -----------------------------

class SignatureAnalysisResult(BaseModel):
    """Forensic signature analysis result"""
    verdict: str  # "Genuine" | "Forged" | "Inconclusive"
    score: float  # 0-100 confidence score
    characteristics: List[str]  # 3-7 forensic observations

class UsageMetrics(BaseModel):
    """Token and latency usage for a single API call"""
    model_config = {"extra": "ignore"}  # provider is logged internally, not exposed in response
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    latency_sec: float
    model: str

class AnalysisResponse(BaseModel):
    """Full API response envelope"""
    result: SignatureAnalysisResult
    usage: UsageMetrics
    timestamp: str
    api_version: str = settings.VERSION

# -----------------------------
# Utility Functions
# -----------------------------

def fix_provider(provider: str) -> str:
    """Fixes the provider name to the correct format."""
    provider = provider.lower()
    if provider == "localllm":
        return "openai"
    return provider

def validate_image_bytes(file_bytes: bytes) -> str:
    """
    Validates image format using magic-number detection.
    Supports PNG and JPEG.
    Returns MIME type string.
    Raises ValueError for unsupported/invalid formats.
    """
    if len(file_bytes) < 8:
        raise ValueError("File too small to be a valid image.")

    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"

    # JPEG: FF D8 FF (stricter check preferred, fallback to FF D8)
    if file_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if file_bytes.startswith(b"\xff\xd8"):
        return "image/jpeg"

    raise ValueError(
        "Unsupported image format. Please upload PNG or JPEG images only."
    )


def validate_image_size(file_bytes: bytes, filename: str = "image"):
    """Validates image file size against configured limits."""
    size_kb = len(file_bytes) / 1024
    size_mb = size_kb / 1024

    if size_kb < settings.MIN_IMAGE_SIZE_KB:
        raise ValueError(
            f"'{filename}' is too small ({size_kb:.1f} KB). "
            f"Minimum size is {settings.MIN_IMAGE_SIZE_KB} KB."
        )
    if size_mb > settings.MAX_IMAGE_SIZE_MB:
        raise ValueError(
            f"'{filename}' is too large ({size_mb:.1f} MB). "
            f"Maximum size is {settings.MAX_IMAGE_SIZE_MB} MB."
        )


def encode_to_data_url(file_bytes: bytes, mime_type: str) -> str:
    """Encodes raw image bytes into a base64 data URL."""
    b64 = base64.b64encode(file_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"


def build_user_prompt() -> str:
    """
    Builds the structured user prompt for forensic comparison.
    Uses settings.CHARACTERISTICS_FORMAT to adjust verbosity.
    """
    verbosity_note = (
        "Each characteristic must be a detailed, technical sentence."
        if settings.CHARACTERISTICS_FORMAT == "verbose"
        else "Keep each characteristic concise (under 10 words), technical sentence."
    )

    return f"""Compare these two signatures as a forensic document examiner.

The FIRST image is the REFERENCE signature (known authentic sample).
The SECOND image is the QUESTIONED signature (to be verified).

Perform a comprehensive forensic analysis and provide your findings in VALID JSON format ONLY.
Do not include markdown formatting, code blocks, or any text outside the JSON object.

Your response must be a single JSON object with this exact structure:
{{
  "verdict": "Genuine" or "Forged" or "Inconclusive",
  "score": <confidence score 0-100, float>,
  "characteristics": [
    "<forensic observation 1>",
    "<forensic observation 2>",
    "<forensic observation 3>",
    "<forensic observation 4>",
    "<forensic observation 5>"
  ]
}}

VERDICT GUIDELINES:
- "Genuine": Strong evidence both signatures are from the same person
- "Forged": Clear evidence of forgery, simulation, or different writer
- "Inconclusive": Insufficient distinctive features or conflicting evidence

SCORE GUIDELINES (0-100):
- 90-100: Extremely high confidence
- 75-89: High confidence
- 60-74: Moderate confidence
- 0-59: Low confidence

CHARACTERISTICS (5 observations, one per forensic dimension):
1. Structural alignment and proportions
2. Writing flow and naturalness (speed/rhythm)
3. Terminal strokes and endpoints
4. Pressure patterns and line quality
5. Unique identifiers or forgery indicators

{verbosity_note}

CRITICAL: Return ONLY the JSON object. No additional text."""


def parse_json_response(raw_text: str) -> Dict[str, Any]:
    """
    Robustly parses a JSON string, stripping markdown code fences if present.
    Raises ValueError on parse failure.
    """
    cleaned = raw_text.strip()

    # Strip ```json ... ``` or ``` ... ```
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"AI model {get_provider()}, returned non-JSON output. Parse error: {e}\n"
            f"Raw response (first 500 chars): {raw_text[:500]}"
        )


def validate_result_structure(result: Dict[str, Any]):
    """Validates that the AI response has the expected fields and value ranges."""
    required_keys = {"verdict", "score", "characteristics"}
    missing = required_keys - result.keys()
    if missing:
        raise ValueError(f"AI response missing required fields: {missing}")

    if result["verdict"] not in ("Genuine", "Forged", "Inconclusive"):
        raise ValueError(f"Invalid verdict value: '{result['verdict']}'")

    if not (0 <= float(result["score"]) <= 100):
        raise ValueError(f"Score out of range [0-100]: {result['score']}")

    if not isinstance(result["characteristics"], list) or len(result["characteristics"]) < 1:
        raise ValueError("'characteristics' must be a non-empty list.")


# -----------------------------
# Provider: LocalLLM
# -----------------------------

def call_local_llm(image1_url: str, image2_url: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Calls LocalLLM Vision (Chat Completions) API."""
    if not localllm_available:
        raise RuntimeError("locallm package not installed.")
    if not client:
        raise RuntimeError("LocalLLM is not configured.")

    client_api, local_model = get_models()
    if client_api is None:
        raise RuntimeError("LocalLLM is not configured.")
    start = time.time()

    response = client_api.chat.completions.create(
        model=local_model,
        messages=[
            {"role": "system", "content": FORENSIC_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": build_user_prompt()},
                    {"type": "image_url", "image_url": {"url": image1_url}},
                    {"type": "image_url", "image_url": {"url": image2_url}},
                ],
            },
        ],
        temperature=0.1,
        max_tokens=1024,
        timeout=settings.LLM_TIMEOUT_SECONDS,
    )

    latency = round(time.time() - start, 3)
    raw_text = response.choices[0].message.content
    result = parse_json_response(raw_text)

    usage = {
        "input_tokens": response.usage.prompt_tokens if response.usage else None,
        "output_tokens": response.usage.completion_tokens if response.usage else None,
        "total_tokens": response.usage.total_tokens if response.usage else None,
        "latency_sec": latency,
        # "model": model,
        "provider": get_provider(),
    }
    return result, usage


# -----------------------------
# Provider: Groq
# -----------------------------

def call_groq(image1_url: str, image2_url: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Calls Groq Vision API."""
    if not _groq_available:
        raise RuntimeError("groq package not installed.")
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    client = Groq(api_key=settings.GROQ_API_KEY)
    model = settings.GROQ_MODEL_NAME
    start = time.time()

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": FORENSIC_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": build_user_prompt()},
                    {"type": "image_url", "image_url": {"url": image1_url}},
                    {"type": "image_url", "image_url": {"url": image2_url}},
                ],
            },
        ],
        temperature=0.1,
        max_tokens=1024,
    )

    latency = round(time.time() - start, 3)
    raw_text = response.choices[0].message.content
    result = parse_json_response(raw_text)

    usage = {
        "input_tokens": response.usage.prompt_tokens if response.usage else None,
        "output_tokens": response.usage.completion_tokens if response.usage else None,
        "total_tokens": response.usage.total_tokens if response.usage else None,
        "latency_sec": latency,
        "model": model,
        "provider": "groq",
    }
    return result, usage


# -----------------------------
# Provider: Google Gemini
# -----------------------------

def call_gemini(image1_bytes: bytes, image2_bytes: bytes,
                mime1: str, mime2: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Calls Google Gemini Vision API using raw bytes."""
    if not _gemini_available:
        raise RuntimeError("google-genai package not installed.")
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    client = google_genai.Client(api_key=settings.GEMINI_API_KEY)
    model = settings.GEMINI_MODEL_NAME
    start = time.time()

    img1_part = google_genai.types.Part.from_bytes(data=image1_bytes, mime_type=mime1)
    img2_part = google_genai.types.Part.from_bytes(data=image2_bytes, mime_type=mime2)

    response = client.models.generate_content(
        model=model,
        contents=[
            google_genai.types.Content(
                role="user",
                parts=[
                    google_genai.types.Part.from_text(
                        FORENSIC_SYSTEM_PROMPT + "\n\n" + build_user_prompt()
                    ),
                    img1_part,
                    img2_part,
                ],
            )
        ],
        config=google_genai.types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=1024,
        ),
    )

    latency = round(time.time() - start, 3)
    raw_text = response.text
    result = parse_json_response(raw_text)

    token_meta = response.usage_metadata if hasattr(response, "usage_metadata") else None
    usage = {
        "input_tokens": getattr(token_meta, "prompt_token_count", None),
        "output_tokens": getattr(token_meta, "candidates_token_count", None),
        "total_tokens": getattr(token_meta, "total_token_count", None),
        "latency_sec": latency,
        "model": model,
        "provider": "gemini",
    }
    return result, usage


# -----------------------------
# Provider: Ollama (local)
# -----------------------------

def call_ollama(image1_bytes: bytes, image2_bytes: bytes) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Calls a local Ollama vision model."""
    if not _ollama_available:
        raise RuntimeError("ollama package not installed.")

    model = settings.OLLAMA_MODEL_NAME
    start = time.time()

    response = ollama_client.chat(
        model=model,
        messages=[
            {
                "role": "user",
                "content": FORENSIC_SYSTEM_PROMPT + "\n\n" + build_user_prompt(),
                "images": [image1_bytes, image2_bytes],
            }
        ],
    )

    latency = round(time.time() - start, 3)
    raw_text = response["message"]["content"]
    result = parse_json_response(raw_text)

    usage = {
        "input_tokens": response.get("prompt_eval_count"),
        "output_tokens": response.get("eval_count"),
        "total_tokens": None,
        "latency_sec": latency,
        "model": model,
        "provider": "ollama",
    }
    return result, usage

# -----------------------------
# Provider Dispatch
# -----------------------------

def analyze_signatures(
    image1_bytes: bytes,
    image2_bytes: bytes,
    mime1: str,
    mime2: str,
    provider: Optional[str] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Dispatches the AI call to the selected provider with retry fallback.
    Provider precedence: explicit arg > PRIMARY_LLM_PROVIDER setting > first available.
    """
    # active_provider = (provider or settings.PRIMARY_LLM_PROVIDER).lower()
    active_provider = fix_provider(provider)

    image1_url = encode_to_data_url(image1_bytes, mime1)
    image2_url = encode_to_data_url(image2_bytes, mime2)

    attempts = settings.FALLBACK_RETRY_ATTEMPTS + 1
    last_error: Exception = RuntimeError("No provider succeeded.")

    for attempt in range(attempts):
        try:
            if active_provider == "openai":
                return call_local_llm(image1_url, image2_url)
            # elif active_provider == "groq":
            #     return call_groq(image1_url, image2_url)
            # elif active_provider == "gemini":
            #     return call_gemini(image1_bytes, image2_bytes, mime1, mime2)
            elif active_provider == "ollama":
                return call_ollama(image1_bytes, image2_bytes)
            else:
                raise ValueError(
                    f"Unknown provider: detected {get_provider()}"
                )
        except Exception as e:
            last_error = e
            if attempt < attempts - 1:
                time.sleep(1.5 ** attempt)  # brief exponential back-off
            continue

    raise last_error


# -----------------------------
# Logging Layer
# -----------------------------

LOG_FILE = "forensic_analysis_logs.jsonl"


def log_analysis(data: Dict[str, Any]):
    """
    Appends a structured JSONL log entry.
    In production, replace with database (PostgreSQL / MongoDB).
    """
    entry = {
        "timestamp": datetime.now().isoformat(),
        **data,
    }
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True) if os.path.dirname(LOG_FILE) else None
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as exc:
        print(f"[WARN] Logging failed: {exc}")


# -----------------------------
# API Endpoints
# -----------------------------

@app.get("/", tags=["Info"])
def root():
    """Root endpoint — API overview."""
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "provider": get_provider(),
        "endpoints": {
            "verify": "/verify-signature",
            "batch": "/verify-signature-batch",
            "health": "/health",
            "docs": "/docs",
        },
    }


@app.get("/health", tags=["Info"])
def health_check():
    """Health check with provider configuration status."""
    provider = get_provider()
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "primary_provider": provider,
        "model": provider.upper(),
    }
    # key_checks = {
    #     "openai": bool(settings.OPENAI_API_KEY),
    #     "gemini": bool(settings.GEMINI_API_KEY),
    #     "groq": bool(settings.GROQ_API_KEY),
    #     "ollama": True,  # local, no key needed
    # }
    # primary_ready = key_checks.get(provider, False)

    # return {
    #     "status": "healthy" if primary_ready else "degraded",
    #     "timestamp": datetime.now().isoformat(),
    #     "primary_provider": provider,
    #     # "provider_keys_configured": key_checks,
    #     "model": getattr(settings, f"{provider.upper()}_MODEL_NAME", "N/A"),
    # }


@app.post("/verify-signature", response_model=AnalysisResponse, tags=["Verification"])
async def verify_signature(
    request: Request,
    reference_signature: UploadFile = File(..., description="Reference (known authentic) signature image — PNG or JPEG"),
    questioned_signature: UploadFile = File(..., description="Questioned signature image — PNG or JPEG"),
    provider: Optional[str] = Query(
        default="LocalLLM",
        description="AI provider - LocalLLM | Ollama"
    ),
):
    """
    **Forensic Signature Verification**

    Upload two signature images:
    - `reference_signature`: The known-authentic baseline.
    - `questioned_signature`: The signature to be verified.

    Returns a forensic verdict (`Genuine` / `Forged` / `Inconclusive`),
    a confidence score (0–100), and detailed characteristics.
    """
    try:
        # --- Read files ---
        ref_bytes = await reference_signature.read()
        quest_bytes = await questioned_signature.read()

        # --- Validate sizes ---
        validate_image_size(ref_bytes, reference_signature.filename or "reference")
        validate_image_size(quest_bytes, questioned_signature.filename or "questioned")

        # --- Detect MIME types ---
        ref_mime = validate_image_bytes(ref_bytes)
        quest_mime = validate_image_bytes(quest_bytes)

        # --- Run AI analysis ---
        result, usage = analyze_signatures(
            ref_bytes, quest_bytes, ref_mime, quest_mime, provider
        )

        # --- Validate AI response ---
        validate_result_structure(result)

        # --- Log success ---
        log_analysis({
            "client_ip": request.client.host if request.client else "unknown",
            "endpoint": "/verify-signature",
            "provider": usage.get("provider"),
            # "model": usage.get("model"),
            "verdict": result.get("verdict"),
            "score": result.get("score"),
            "reference_file": reference_signature.filename,
            "questioned_file": questioned_signature.filename,
            "usage": usage,
            "status": "success",
        })

        return AnalysisResponse(
            result=SignatureAnalysisResult(**result),
            usage=UsageMetrics(**usage),
            timestamp=datetime.now().isoformat(),
        )

    except ValueError as ve:
        log_analysis({
            "client_ip": request.client.host if request.client else "unknown",
            "endpoint": "/verify-signature",
            "error": str(ve),
            "status": "validation_error",
        })
        raise HTTPException(status_code=400, detail=str(ve))

    except Exception as e:
        log_analysis({
            "client_ip": request.client.host if request.client else "unknown",
            "endpoint": "/verify-signature",
            "error": str(e),
            "status": "failed",
        })
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/verify-signature-batch", tags=["Verification"])
async def verify_signature_batch(
    request: Request,
    files: List[UploadFile] = File(
        ...,
        description="Even-indexed = reference; odd-indexed = questioned. Total must be even.",
    ),
    provider: Optional[str] = Query(
        default=None,
        description="AI provider: LocalLLM | Ollama"
    ),
):
    """
    **Batch Signature Verification**

    Upload pairs of signatures for bulk analysis.
    Files at indices 0, 2, 4… are reference signatures;
    files at indices 1, 3, 5… are questioned signatures.
    """
    if len(files) % 2 != 0:
        raise HTTPException(
            status_code=400,
            detail="Must upload an even number of files (pairs of reference + questioned signatures).",
        )

    results = []

    for i in range(0, len(files), 2):
        ref_file = files[i]
        quest_file = files[i + 1]
        pair_index = i // 2

        try:
            ref_bytes = await ref_file.read()
            quest_bytes = await quest_file.read()

            validate_image_size(ref_bytes, ref_file.filename or f"pair-{pair_index}-ref")
            validate_image_size(quest_bytes, quest_file.filename or f"pair-{pair_index}-quest")

            ref_mime = validate_image_bytes(ref_bytes)
            quest_mime = validate_image_bytes(quest_bytes)

            result, usage = analyze_signatures(
                ref_bytes, quest_bytes, ref_mime, quest_mime, provider
            )
            validate_result_structure(result)

            results.append({
                "pair_index": pair_index,
                "reference_file": ref_file.filename,
                "questioned_file": quest_file.filename,
                "result": result,
                "usage": usage,
                "timestamp": datetime.now().isoformat(),
                "status": "success",
            })

        except Exception as e:
            results.append({
                "pair_index": pair_index,
                "reference_file": ref_file.filename,
                "questioned_file": quest_file.filename,
                "error": str(e),
                "status": "failed",
                "timestamp": datetime.now().isoformat(),
            })

    total = len(results)
    succeeded = sum(1 for r in results if r.get("status") == "success")

    log_analysis({
        "client_ip": request.client.host if request.client else "unknown",
        "endpoint": "/verify-signature-batch",
        "total_pairs": total,
        "succeeded": succeeded,
        "failed": total - succeeded,
    })

    return {
        "total_pairs": total,
        "succeeded": succeeded,
        "failed": total - succeeded,
        "results": results,
    }


# -----------------------------
# Global Exception Handler
# -----------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Unified JSON error envelope for all HTTP errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat(),
        },
    )


# -----------------------------
# Startup Event
# -----------------------------

@app.on_event("startup")
async def startup_event():
    """Logs startup configuration to console."""
    provider = settings.PRIMARY_LLM_PROVIDER
    model_attr = f"{provider.upper()}_MODEL_NAME"
    model = getattr(settings, model_attr, "N/A")

    key_attr = f"{provider.upper()}_API_KEY"
    key_set = bool(getattr(settings, key_attr, "")) if provider != "ollama" else True

    print("=" * 70)
    print(f"  {settings.PROJECT_NAME}  v{settings.VERSION}")
    print("=" * 70)
    # print(f"  Provider : {provider.upper()}")
    # print(f"  Model    : {model}")
    # print(f"  API Key  : {'✓ Configured' if key_set else '✗ NOT SET — provider will fail'}")
    print(f"  Timeout  : {settings.LLM_TIMEOUT_SECONDS}s")
    print(f"  Max Size : {settings.MAX_IMAGE_SIZE_MB} MB | Min Size: {settings.MIN_IMAGE_SIZE_KB} KB")
    print(f"  Log File : {LOG_FILE}")
    print("=" * 70)


# -----------------------------
# Entry Point
# -----------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
