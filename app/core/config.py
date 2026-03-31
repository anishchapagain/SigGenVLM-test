from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App config
    PROJECT_NAME: str = "Signature Verification API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # DB
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/gensigllm"
    
    # Security
    SECRET_KEY: str = "change_me_in_production"
    
    # Validation
    MAX_IMAGE_SIZE_MB: int = 5
    MIN_IMAGE_SIZE_KB: int = 10
    ALLOWED_IMAGE_TYPES: list[str] = ["image/jpeg", "image/png", "image/webp"]
    
    # AI Config
    # PRIMARY_LLM_PROVIDER: str = "openai"
    PRIMARY_LLM_PROVIDER: str = "ollama"
    # PRIMARY_LLM_PROVIDER: str = "groq"
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    OPENAI_MODEL_NAME: str = "gpt-4o"
    GEMINI_MODEL_NAME: str = "gemini-1.5-pro-latest"
    OLLAMA_MODEL_NAME: str = "qwen2.5-vl"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    GROQ_API_KEY: str = ""
    GROQ_MODEL_NAME: str = "llama-3.2-11b-vision-preview"
    LLM_TIMEOUT_SECONDS: int = 30
    FALLBACK_RETRY_ATTEMPTS: int = 2
    CHARACTERISTICS_FORMAT: str = "verbose" # succinct or verbose
    
    FORENSIC_PROMPT: str = """
You are an expert forensic document examiner specializing in signature verification for the financial sector. 
Analyze the two provided signatures: Image 1 is the Genuine reference, Image 2 is the Questioned signature.

Follow strict forensic evaluation criteria:
1. Letter Structure: alignment and baseline deviation.
2. Line Quality: natural flow vs labored drawing.
3. Slant & Proportion: ratio and angular consistency.
4. Terminal Strokes: tapered endpoints vs blunt stops.
5. Execution Velocity: rapid habitual vs slow calculated.

Provide the exact JSON response and nothing else:
{
  "verdict": "Genuine" or "Forgery",
  "score": <0-100 float>,
  "characteristics": ["analysis point 1", "analysis point 2", ...]
}
"""

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
