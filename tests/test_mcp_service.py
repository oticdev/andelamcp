import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.mcp_service import MCPClient, get_mcp_client


def _http_cm(result: dict, session_id: str | None = None, error: dict | None = None):
    """Build a mock httpx async context manager for a single request."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.headers = {"mcp-session-id": session_id} if session_id else {}
    payload = {"jsonrpc": "2.0", "id": 1}
    if error:
        payload["error"] = error
    else:
        payload["result"] = result
    mock_response.json.return_value = payload

    mock_http = AsyncMock()
    mock_http.post = AsyncMock(return_value=mock_response)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=mock_http)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


async def test_initialize_captures_session_id():
    client = MCPClient("http://test/mcp")
    cm = _http_cm({}, session_id="sess-abc")

    with patch("src.services.mcp_service.httpx.AsyncClient", return_value=cm):
        await client._ensure_initialized()

    assert client._session_id == "sess-abc"


async def test_initialize_called_only_once():
    client = MCPClient("http://test/mcp")
    cm = _http_cm({}, session_id="sess-1")

    with patch("src.services.mcp_service.httpx.AsyncClient", return_value=cm) as MockClient:
        await client._ensure_initialized()
        await client._ensure_initialized()

    assert MockClient.call_count == 1


async def test_session_id_sent_in_subsequent_requests():
    client = MCPClient("http://test/mcp")
    client._session_id = "existing-sess"

    captured_headers = []

    async def fake_post(url, json, headers):
        captured_headers.append(dict(headers))
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.headers = {}
        resp.json.return_value = {"jsonrpc": "2.0", "id": 1, "result": {"content": []}}
        return resp

    mock_http = AsyncMock()
    mock_http.post = AsyncMock(side_effect=fake_post)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=mock_http)
    cm.__aexit__ = AsyncMock(return_value=None)

    with patch("src.services.mcp_service.httpx.AsyncClient", return_value=cm):
        await client.call_tool("any_tool", {})

    assert captured_headers[0].get("mcp-session-id") == "existing-sess"


async def test_list_tools_caches_result():
    client = MCPClient("http://test/mcp")
    tools = [{"name": "search_products"}]
    cm = _http_cm({"tools": tools}, session_id="sess-1")

    with patch("src.services.mcp_service.httpx.AsyncClient", return_value=cm) as MockClient:
        result1 = await client.list_tools()
        result2 = await client.list_tools()

    assert result1 == tools
    assert result2 == tools
    # Only 2 calls: initialize + tools/list; second list_tools hits cache
    assert MockClient.call_count == 2


async def test_call_tool_extracts_text_content():
    client = MCPClient("http://test/mcp")
    client._session_id = "sess-1"
    content = [
        {"type": "text", "text": "Dell 27 Monitor"},
        {"type": "image", "url": "http://img.example.com/dell.jpg"},
        {"type": "text", "text": "LG UltraWide"},
    ]
    cm = _http_cm({"content": content})

    with patch("src.services.mcp_service.httpx.AsyncClient", return_value=cm):
        result = await client.call_tool("search_products", {"query": "monitor"})

    assert result == "Dell 27 Monitor\nLG UltraWide"


async def test_call_tool_empty_content_falls_back_to_json():
    client = MCPClient("http://test/mcp")
    client._session_id = "sess-1"
    cm = _http_cm({"content": []})

    with patch("src.services.mcp_service.httpx.AsyncClient", return_value=cm):
        result = await client.call_tool("any_tool", {})

    assert result  # non-empty fallback


async def test_mcp_error_raises_runtime_error():
    client = MCPClient("http://test/mcp")
    client._session_id = "sess-1"
    cm = _http_cm({}, error={"code": -32601, "message": "method not found"})

    with patch("src.services.mcp_service.httpx.AsyncClient", return_value=cm):
        with pytest.raises(RuntimeError, match="MCP error"):
            await client.call_tool("unknown_tool", {})


async def test_request_id_increments():
    client = MCPClient("http://test/mcp")
    assert client._next_id() == 1
    assert client._next_id() == 2
    assert client._next_id() == 3


def test_get_mcp_client_returns_singleton_for_same_url():
    c1 = get_mcp_client("http://server/mcp")
    c2 = get_mcp_client("http://server/mcp")
    assert c1 is c2


def test_get_mcp_client_new_instance_for_different_url():
    c1 = get_mcp_client("http://server-a/mcp")
    c2 = get_mcp_client("http://server-b/mcp")
    assert c1 is not c2
