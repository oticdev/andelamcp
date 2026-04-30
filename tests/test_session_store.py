from src.services.session_store import get_session, save_session


def test_get_session_none_creates_new():
    sid, history = get_session(None)
    assert sid is not None
    assert history == []


def test_get_session_unknown_id_creates_new():
    sid, history = get_session("does-not-exist")
    assert sid != "does-not-exist"
    assert history == []


def test_get_session_existing_id_returns_history():
    save_session("known-sid", [{"role": "user", "content": "hi"}])
    sid, history = get_session("known-sid")
    assert sid == "known-sid"
    assert history == [{"role": "user", "content": "hi"}]


def test_get_session_returns_copy():
    save_session("sid", [{"role": "user", "content": "hi"}])
    _, history = get_session("sid")
    history.append({"role": "assistant", "content": "yo"})
    _, history2 = get_session("sid")
    assert len(history2) == 1  # mutation didn't affect stored session


def test_save_session_overwrites():
    save_session("sid", [{"role": "user", "content": "first"}])
    save_session("sid", [{"role": "user", "content": "second"}])
    _, history = get_session("sid")
    assert history[0]["content"] == "second"


def test_two_none_sessions_are_distinct():
    sid1, _ = get_session(None)
    sid2, _ = get_session(None)
    assert sid1 != sid2


def test_round_trip_preserves_messages():
    messages = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
        {"role": "user", "content": "how are you"},
    ]
    save_session("rt-sid", messages)
    _, history = get_session("rt-sid")
    assert history == messages
