from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logger import logger
from app.db.database import engine, Base
from app.api.v1.endpoints import router as api_router

# Initialize schema
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.PROJECT_DESCRIPTION
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.PROJECT_NAME} - Server.")

@app.get("/health", tags=["Health"])
def health_check():
    logger.info("Health check requested.")
    return {"status": "ok", "service": settings.PROJECT_NAME}
