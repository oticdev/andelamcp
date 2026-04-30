from fastapi import Request
from openai import AsyncOpenAI


async def get_openai_client(request: Request) -> AsyncOpenAI:
    return request.app.state.openai_client
