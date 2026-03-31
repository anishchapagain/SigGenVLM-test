import json
import base64
from fastapi import UploadFile
from openai import AsyncOpenAI
from openai import APIError, APITimeoutError
import google.generativeai as genai
import ollama
from groq import AsyncGroq, RateLimitError
import re
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings
from app.core.logger import logger
from app.schemas.payload import VerificationResult

oai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
genai.configure(api_key=settings.GEMINI_API_KEY)
ollama_client = ollama.AsyncClient(host=settings.OLLAMA_BASE_URL)
groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)

async def encode_image(file: UploadFile) -> str:
    file.file.seek(0)
    contents = await file.read()
    return base64.b64encode(contents).decode('utf-8')

@retry(
    stop=stop_after_attempt(settings.FALLBACK_RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((APIError, APITimeoutError)),
    reraise=True
)
async def call_openai(genuine_b64: str, questioned_b64: str) -> str:
    logger.info(f"Calling OpenAI ({settings.OPENAI_MODEL_NAME}) for signature verification.")
    response = await oai_client.chat.completions.create(
        model=settings.OPENAI_MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": settings.FORENSIC_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{genuine_b64}"}
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{questioned_b64}"}
                    }
                ]
            }
        ],
        response_format={ "type": "json_object" },
        timeout=settings.LLM_TIMEOUT_SECONDS
    )
    return response.choices[0].message.content

async def call_gemini(genuine_b64: str, questioned_b64: str) -> str:
    logger.info(f"Calling Google Gemini ({settings.GEMINI_MODEL_NAME}).")
    model = genai.GenerativeModel(settings.GEMINI_MODEL_NAME, generation_config={"response_mime_type": "application/json"})
    
    gen_bytes = base64.b64decode(genuine_b64)
    quest_bytes = base64.b64decode(questioned_b64)
    
    parts = [
        settings.FORENSIC_PROMPT,
        {"mime_type": "image/jpeg", "data": gen_bytes},
        {"mime_type": "image/jpeg", "data": quest_bytes}
    ]
    
    response = await model.generate_content_async(parts)
    return response.text

async def call_ollama(genuine_b64: str, questioned_b64: str) -> str:
    logger.info(f"Calling local Ollama ({settings.OLLAMA_MODEL_NAME}) for signature verification.")
    
    gen_bytes = base64.b64decode(genuine_b64)
    quest_bytes = base64.b64decode(questioned_b64)
    
    response = await ollama_client.chat(
        model=settings.OLLAMA_MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": settings.FORENSIC_PROMPT,
                "images": [gen_bytes, quest_bytes]
            }
        ],
        format='json'
    )
    return response.get("message", {}).get("content", "")

async def call_groq(genuine_b64: str, questioned_b64: str) -> str:
    logger.info(f"Calling Groq ({settings.GROQ_MODEL_NAME}) for fast verification.")
    response = await groq_client.chat.completions.with_raw_response.create(
        model=settings.GROQ_MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": settings.FORENSIC_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{genuine_b64}"}
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{questioned_b64}"}
                    }
                ]
            }
        ],
        timeout=settings.LLM_TIMEOUT_SECONDS
    )
    
    headers = response.headers
    rem_tokens = headers.get('x-ratelimit-remaining-tokens', 'Unknown')
    rem_reqs = headers.get('x-ratelimit-remaining-requests', 'Unknown')
    reset_time = headers.get('x-ratelimit-reset-tokens', 'Unknown')
    logger.info(f"[Groq Telemetry] Tokens Left: {rem_tokens} | Reqs Left: {rem_reqs} | Reset In: {reset_time}")
    
    completion = response.parse()
    usage = completion.usage
    if usage:
        logger.info(f"[Groq Usage] Prompt: {usage.prompt_tokens} | Completion: {usage.completion_tokens} | Total: {usage.total_tokens}")
        
    return completion.choices[0].message.content

async def verify_signatures(genuine_file: UploadFile, questioned_file: UploadFile) -> tuple[VerificationResult, str, Exception]:
    genuine_b64 = await encode_image(genuine_file)
    questioned_b64 = await encode_image(questioned_file)
    
    fallback_e = None
    provider = settings.PRIMARY_LLM_PROVIDER
    
    if provider == "ollama":
        # Enforce local isolation: No cloud fallback
        try:
            result_str = await call_ollama(genuine_b64, questioned_b64)
        except Exception as e:
            logger.error(f"Local Ollama {settings.OLLAMA_MODEL_NAME} failed: {str(e)}. Cloud fallback disabled.")
            raise Exception(f"Local Ollama Request Failed: {str(e)}")
    else:
        try:
            if settings.PRIMARY_LLM_PROVIDER == "groq":
                result_str = await call_groq(genuine_b64, questioned_b64)
            elif settings.PRIMARY_LLM_PROVIDER == "openai":
                result_str = await call_openai(genuine_b64, questioned_b64)
            else:
                result_str = await call_gemini(genuine_b64, questioned_b64)
        except Exception as e:
            # specifically log RateLimitErrors brightly if using Groq
            if isinstance(e, RateLimitError):
                logger.warning(f"Groq Playground Rate Limit Exhausted! Halting local run and triggering fallback: {str(e)}")
            else:
                logger.error(f"Primary provider {settings.PRIMARY_LLM_PROVIDER} failed: {str(e)}.")
                
            fallback_e = e
            try:
                if settings.PRIMARY_LLM_PROVIDER in ["openai", "groq"]:
                    result_str = await call_gemini(genuine_b64, questioned_b64)
                    provider = "gemini"
                else:
                    result_str = await call_openai(genuine_b64, questioned_b64)
                    provider = "openai"
            except Exception as fallback_failure:
                logger.critical(f"Fallback provider also failed. {str(fallback_failure)}")
                raise fallback_failure
            
    try:
        text = result_str.strip()
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fenced:
            text = fenced.group(1).strip()
        
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx != -1 and end_idx != -1:
            text = text[start_idx:end_idx+1]

        data = json.loads(text)
        return VerificationResult(**data), provider, fallback_e
    except Exception as e:
        logger.error(f"Failed to parse AI output: {result_str} - Error: {e}")
        raise ValueError("Invalid format from AI payload.")
