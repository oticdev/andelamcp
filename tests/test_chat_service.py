from unittest.mock import AsyncMock, patch

from src.services.chat_service import _to_openai_tools, chat
from src.services.session_store import get_session, save_session
from tests.helpers import llm_response, make_settings, mock_mcp, mock_openai, tool_call


# ---------------------------------------------------------------------------
# _to_openai_tools — pure function
# ---------------------------------------------------------------------------

def test_to_openai_tools_empty_list():
    assert _to_openai_tools([]) == []


def test_to_openai_tools_converts_schema():
    mcp_tool = {
        "name": "search_products",
        "description": "Search catalog",
        "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}},
    }
    assert _to_openai_tools([mcp_tool]) == [
        {
            "type": "function",
            "function": {
                "name": "search_products",
                "description": "Search catalog",
                "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
            },
        }
    ]


def test_to_openai_tools_defaults_when_fields_missing():
    result = _to_openai_tools([{"name": "foo"}])
    assert result[0]["function"]["description"] == ""
    assert result[0]["function"]["parameters"] == {"type": "object", "properties": {}}


def test_to_openai_tools_preserves_order():
    tools = [{"name": "a"}, {"name": "b"}, {"name": "c"}]
    assert [r["function"]["name"] for r in _to_openai_tools(tools)] == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# chat() — agentic loop
# ---------------------------------------------------------------------------

settings = make_settings()


async def test_chat_direct_response():
    client = mock_openai(llm_response("We have Dell and LG monitors."))
    mcp = mock_mcp()

    with patch("src.services.chat_service.get_mcp_client", return_value=mcp):
        reply, session_id = await chat("show me monitors", None, settings, client)

    assert reply == "We have Dell and LG monitors."
    assert session_id is not None


async def test_chat_creates_new_session_for_none():
    client = mock_openai(llm_response("Hello!"))
    mcp = mock_mcp()

    with patch("src.services.chat_service.get_mcp_client", return_value=mcp):
        _, sid1 = await chat("hi", None, settings, client)

    client2 = mock_openai(llm_response("Hello!"))
    with patch("src.services.chat_service.get_mcp_client", return_value=mcp):
        _, sid2 = await chat("hi", None, settings, client2)

    assert sid1 != sid2


async def test_chat_reuses_existing_session():
    save_session("existing-sid", [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ])

    captured = []

    async def capture_and_respond(model, messages, tools, tool_choice):
        captured.extend(messages)
        return llm_response("Got it!")

    client = AsyncMock()
    client.chat.completions.create = AsyncMock(side_effect=capture_and_respond)
    mcp = mock_mcp()

    with patch("src.services.chat_service.get_mcp_client", return_value=mcp):
        _, returned_sid = await chat("follow up", "existing-sid", settings, client)

    assert returned_sid == "existing-sid"
    assert len(captured) == 4  # system + 2 history + new user message
    assert captured[0]["role"] == "system"
    assert captured[-1]["content"] == "follow up"


async def test_chat_executes_tool_call_and_continues():
    tc = tool_call("tc-1", "search_products", '{"query": "monitor"}')
    client = mock_openai([
        llm_response(None, tool_calls=[tc]),
        llm_response("Found a Dell 27 Monitor for $299.99."),
    ])
    mcp = mock_mcp(tool_responses={"search_products": '[{"name": "Dell 27", "price": 299.99}]'})

    with patch("src.services.chat_service.get_mcp_client", return_value=mcp):
        reply, _ = await chat("show monitors", None, settings, client)

    assert reply == "Found a Dell 27 Monitor for $299.99."
    mcp.call_tool.assert_awaited_once_with("search_products", {"query": "monitor"})


async def test_chat_multiple_tool_calls_in_one_turn():
    tc1 = tool_call("tc-1", "search_products", '{"query": "keyboard"}')
    tc2 = tool_call("tc-2", "search_products", '{"query": "monitor"}')
    client = mock_openai([
        llm_response(None, tool_calls=[tc1, tc2]),
        llm_response("Here's what I found."),
    ])
    mcp = mock_mcp(tool_responses={"search_products": "[]"})

    with patch("src.services.chat_service.get_mcp_client", return_value=mcp):
        await chat("show keyboards and monitors", None, settings, client)

    assert mcp.call_tool.await_count == 2


async def test_chat_multi_round_tool_loop():
    tc1 = tool_call("tc-1", "verify_customer_pin", '{"email": "a@b.com", "pin": "1234"}')
    tc2 = tool_call("tc-2", "get_order_history", '{"email": "a@b.com"}')
    client = mock_openai([
        llm_response(None, tool_calls=[tc1]),
        llm_response(None, tool_calls=[tc2]),
        llm_response("Your order ORD-1 is on its way."),
    ])
    mcp = mock_mcp(tool_responses={
        "verify_customer_pin": '{"success": true}',
        "get_order_history": '[{"order_id": "ORD-1"}]',
    })

    with patch("src.services.chat_service.get_mcp_client", return_value=mcp):
        reply, _ = await chat("show my orders", None, settings, client)

    assert reply == "Your order ORD-1 is on its way."
    assert mcp.call_tool.await_count == 2


async def test_chat_tool_error_is_passed_back_to_llm():
    tc = tool_call("tc-1", "broken_tool", '{}')
    messages_round2 = []

    async def respond(model, messages, tools, tool_choice):
        if respond.calls == 0:
            respond.calls += 1
            return llm_response(None, tool_calls=[tc])
        messages_round2.extend(messages)
        return llm_response("I'm unable to fetch that right now.")

    respond.calls = 0

    client = AsyncMock()
    client.chat.completions.create = AsyncMock(side_effect=respond)
    mcp = mock_mcp()
    mcp.call_tool = AsyncMock(side_effect=RuntimeError("upstream timeout"))

    with patch("src.services.chat_service.get_mcp_client", return_value=mcp):
        await chat("do something", None, settings, client)

    tool_result = next(m for m in messages_round2 if m.get("role") == "tool")
    assert "Tool error" in tool_result["content"]


async def test_chat_persists_history():
    client = mock_openai(llm_response("Hello!"))
    mcp = mock_mcp()

    with patch("src.services.chat_service.get_mcp_client", return_value=mcp):
        _, session_id = await chat("hi", None, settings, client)

    _, history = get_session(session_id)
    assert any(m["role"] == "user" and m["content"] == "hi" for m in history)
    assert any(m["role"] == "assistant" and m["content"] == "Hello!" for m in history)


async def test_chat_system_prompt_not_in_persisted_history():
    client = mock_openai(llm_response("Hi!"))
    mcp = mock_mcp()

    with patch("src.services.chat_service.get_mcp_client", return_value=mcp):
        _, session_id = await chat("hi", None, settings, client)

    _, history = get_session(session_id)
    assert not any(m["role"] == "system" for m in history)
