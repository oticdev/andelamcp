from unittest.mock import AsyncMock, MagicMock

from src.core.config import Settings


def make_settings(**overrides) -> Settings:
    defaults = dict(
        openai_api_key="sk-test-key",
        openai_model="gpt-4o-mini",
        mcp_server_url="http://localhost:8001/mcp",
    )
    return Settings(**{**defaults, **overrides})


def llm_response(content: str | None, tool_calls=None) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = tool_calls
    return MagicMock(choices=[MagicMock(message=msg)])


def tool_call(call_id: str, name: str, arguments: str) -> MagicMock:
    tc = MagicMock()
    tc.id = call_id
    tc.function = MagicMock()
    tc.function.name = name
    tc.function.arguments = arguments
    return tc


def mock_openai(responses) -> AsyncMock:
    """Build a mock AsyncOpenAI client with canned responses."""
    client = AsyncMock()
    if isinstance(responses, list):
        client.chat.completions.create = AsyncMock(side_effect=responses)
    else:
        client.chat.completions.create = AsyncMock(return_value=responses)
    return client


def mock_mcp(tools=None, tool_responses=None) -> AsyncMock:
    """Build a mock MCPClient with configurable tool list and per-tool responses."""
    tools = tools or []
    tool_responses = tool_responses or {}

    mock = AsyncMock()
    mock.list_tools = AsyncMock(return_value=tools)

    async def _call_tool(name, arguments):
        resp = tool_responses.get(name, '{"result": "ok"}')
        return resp() if callable(resp) else resp

    mock.call_tool = AsyncMock(side_effect=_call_tool)
    return mock
