import json
import logging

import httpx

logger = logging.getLogger(__name__)

_client: "MCPClient | None" = None


class MCPClient:
    def __init__(self, url: str) -> None:
        self._url = url
        self._session_id: str | None = None
        self._tools: list[dict] | None = None
        self._req_id = 0

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    async def _post(self, method: str, params: dict) -> dict:
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params,
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            headers["mcp-session-id"] = self._session_id

        async with httpx.AsyncClient(timeout=30) as http:
            response = await http.post(self._url, json=payload, headers=headers)
            response.raise_for_status()

            if sid := response.headers.get("mcp-session-id"):
                self._session_id = sid

            data = response.json()
            if "error" in data:
                raise RuntimeError(f"MCP error: {data['error']}")
            return data.get("result", {})

    async def _ensure_initialized(self) -> None:
        if self._session_id is not None:
            return
        logger.info("MCP initializing", extra={"url": self._url})
        await self._post("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "meridian-chatbot", "version": "1.0"},
        })

    async def list_tools(self) -> list[dict]:
        if self._tools is not None:
            return self._tools
        await self._ensure_initialized()
        result = await self._post("tools/list", {})
        self._tools = result.get("tools", [])
        logger.info("MCP tools loaded", extra={"count": len(self._tools)})
        return self._tools

    async def call_tool(self, name: str, arguments: dict) -> str:
        await self._ensure_initialized()
        logger.debug("MCP tool call", extra={"tool": name})
        try:
            result = await self._post("tools/call", {"name": name, "arguments": arguments})
        except Exception:
            logger.error("MCP tool call failed", extra={"tool": name}, exc_info=True)
            raise
        content = result.get("content", [])
        if isinstance(content, list):
            texts = [item["text"] for item in content if item.get("type") == "text"]
            return "\n".join(texts) if texts else json.dumps(result)
        return str(result)


def get_mcp_client(url: str) -> MCPClient:
    global _client
    if _client is None or _client._url != url:
        _client = MCPClient(url)
    return _client
