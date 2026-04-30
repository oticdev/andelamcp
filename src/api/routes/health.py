from fastapi import APIRouter

from src.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/")
def root():
    return {
        "message": "Assessment API is running",
        "docs": "/docs",
    }


@router.get("/health", response_model=HealthResponse)
def health():
    return {"status": "ok"}
