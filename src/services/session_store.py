import uuid

# session_id -> list of messages (excludes system prompt)
_sessions: dict[str, list[dict]] = {}


def get_session(session_id: str | None) -> tuple[str, list[dict]]:
    if session_id is None or session_id not in _sessions:
        session_id = str(uuid.uuid4())
        _sessions[session_id] = []
    return session_id, list(_sessions[session_id])


def save_session(session_id: str, messages: list[dict]) -> None:
    _sessions[session_id] = messages
