import json
import logging

from openai import AsyncOpenAI

from src.core.config import Settings
from src.services.mcp_service import get_mcp_client
from src.services.session_store import get_session, save_session

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a helpful customer support assistant for Meridian Electronics, \
a company that sells computer products — monitors, keyboards, printers, networking gear, and accessories.

You can help customers:
- Browse and search the product catalog
- Check product availability and pricing
- Verify their identity (email + 4-digit PIN) before accessing account features
- View their order history
- Place new orders

Rules:
- Always verify the customer's identity using verify_customer_pin before looking up orders or placing orders
- Before placing an order, confirm the items, quantities, and total cost with the customer
- Be concise, professional, and friendly
- If a product is unavailable, suggest alternatives when possible
- Format currency as USD with 2 decimal places"""


def _to_openai_tools(mcp_tools: list[dict]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("inputSchema", {"type": "object", "properties": {}}),
            },
        }
        for t in mcp_tools
    ]


async def chat(
    message: str,
    session_id: str | None,
    settings: Settings,
    openai_client: AsyncOpenAI,
) -> tuple[str, str]:
    mcp = get_mcp_client(settings.mcp_server_url)
    mcp_tools = await mcp.list_tools()
    openai_tools = _to_openai_tools(mcp_tools)

    session_id, history = get_session(session_id)
    is_new = not history

    logger.info(
        "Chat request",
        extra={
            "session_id": session_id,
            "new_session": is_new,
            "message_len": len(message),
        },
    )

    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": message},
    ]

    final_content = ""
    rounds = 0
    tool_calls_made = 0

    while True:
        rounds += 1
        response = await openai_client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,  # type: ignore[arg-type]
            tools=openai_tools,  # type: ignore[arg-type]
            tool_choice="auto",
        )

        msg = response.choices[0].message

        assistant_entry: dict = {"role": "assistant", "content": msg.content}
        if msg.tool_calls:
            assistant_entry["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ]
        messages.append(assistant_entry)

        if not msg.tool_calls:
            final_content = msg.content or ""
            break

        for tc in msg.tool_calls:
            tool_calls_made += 1
            args = json.loads(tc.function.arguments)
            logger.info("Tool call", extra={"session_id": session_id, "tool": tc.function.name})
            try:
                result = await mcp.call_tool(tc.function.name, args)
            except Exception as e:
                logger.warning(
                    "Tool error",
                    extra={"session_id": session_id, "tool": tc.function.name, "error": str(e)},
                )
                result = f"Tool error: {e}"
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    logger.info(
        "Chat complete",
        extra={
            "session_id": session_id,
            "rounds": rounds,
            "tool_calls": tool_calls_made,
            "response_len": len(final_content),
        },
    )

    save_session(session_id, messages[1:])
    return final_content, session_id
