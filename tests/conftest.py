import pytest

import src.services.session_store as _session_store
import src.services.mcp_service as _mcp_service
from tests.helpers import make_settings


@pytest.fixture(autouse=True)
def _isolate_globals():
    """Reset module-level singletons between every test."""
    _session_store._sessions.clear()
    _mcp_service._client = None
    yield
    _session_store._sessions.clear()
    _mcp_service._client = None


@pytest.fixture
def mock_settings():
    return make_settings()
