from fastapi import APIRouter, Depends, HTTPException, status
from openai import AsyncOpenAI

from src.core.config import Settings, get_settings
from src.core.dependencies import get_openai_client
from src.schemas.chat import ChatRequest, ChatResponse
from src.services.chat_service import chat

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    settings: Settings = Depends(get_settings),
    openai_client: AsyncOpenAI = Depends(get_openai_client),
):
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OPENAI_API_KEY is not configured",
        )

    response, session_id = await chat(request.message, request.session_id, settings, openai_client)
    return ChatResponse(response=response, session_id=session_id)
