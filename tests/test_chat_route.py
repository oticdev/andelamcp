from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.core.config import Settings, get_settings
from src.core.dependencies import get_openai_client
from tests.helpers import llm_response, mock_mcp, mock_openai


@pytest.fixture
def mock_client(mock_settings):
    """Wire mock settings and a mock OpenAI client into the app."""
    oai = mock_openai(llm_response("OK!"))
    app.dependency_overrides[get_settings] = lambda: mock_settings
    app.dependency_overrides[get_openai_client] = lambda: oai
    yield oai
    app.dependency_overrides.clear()


@pytest.fixture
def client(mock_client):
    return TestClient(app)


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------

def test_chat_returns_200_with_response_and_session_id(client, mock_client):
    mock_client.chat.completions.create.return_value = llm_response("We have monitors!")
    mcp = mock_mcp()
    with patch("src.services.chat_service.get_mcp_client", return_value=mcp):
        resp = client.post("/chat/", json={"message": "show monitors", "session_id": None})

    assert resp.status_code == 200
    body = resp.json()
    assert body["response"] == "We have monitors!"
    assert body["session_id"] is not None


def test_chat_session_id_is_stable_across_turns(client, mock_client):
    mcp = mock_mcp()
    with patch("src.services.chat_service.get_mcp_client", return_value=mcp):
        resp1 = client.post("/chat/", json={"message": "hi", "session_id": None})
        session_id = resp1.json()["session_id"]
        resp2 = client.post("/chat/", json={"message": "and then?", "session_id": session_id})

    assert resp2.json()["session_id"] == session_id


# ---------------------------------------------------------------------------
# Middleware headers
# ---------------------------------------------------------------------------

def test_response_includes_timing_and_request_id_headers(client, mock_client):
    mcp = mock_mcp()
    with patch("src.services.chat_service.get_mcp_client", return_value=mcp):
        resp = client.post("/chat/", json={"message": "hi", "session_id": None})

    assert "x-request-id" in resp.headers
    assert "x-response-time-ms" in resp.headers


def test_custom_request_id_is_echoed(client, mock_client):
    mcp = mock_mcp()
    with patch("src.services.chat_service.get_mcp_client", return_value=mcp):
        resp = client.post(
            "/chat/",
            json={"message": "hi", "session_id": None},
            headers={"x-request-id": "my-trace-id"},
        )

    assert resp.headers["x-request-id"] == "my-trace-id"


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------

def test_missing_api_key_returns_500(mock_settings):
    mock_settings.openai_api_key = None
    oai = mock_openai(llm_response("Hi!"))
    app.dependency_overrides[get_settings] = lambda: mock_settings
    app.dependency_overrides[get_openai_client] = lambda: oai
    c = TestClient(app)

    resp = c.post("/chat/", json={"message": "hello", "session_id": None})

    app.dependency_overrides.clear()
    assert resp.status_code == 500
    assert "OPENAI_API_KEY" in resp.json()["detail"]


def test_missing_message_field_returns_422(client):
    resp = client.post("/chat/", json={"session_id": None})
    assert resp.status_code == 422


def test_wrong_message_type_returns_422(client):
    resp = client.post("/chat/", json={"message": 123, "session_id": None})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health_check():
    resp = TestClient(app).get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
