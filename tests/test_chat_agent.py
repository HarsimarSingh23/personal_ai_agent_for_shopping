import json

import pytest

import chat_agent
from llm import LLMConfigError


@pytest.fixture(autouse=True)
def no_retry_wait(monkeypatch):
    # tenacity sleeps between retries; skip the waiting in tests.
    monkeypatch.setattr(chat_agent._get_chat_response.retry, "sleep", lambda _: None)


def _reply(monkeypatch, payload):
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    monkeypatch.setattr(chat_agent, "_ask", lambda prompt: raw)


def test_string_false_is_not_treated_as_true(monkeypatch):
    _reply(monkeypatch, {"message": "Which budget?", "is_ready_to_search": "false", "search_query": ""})
    out = chat_agent.process_chat([{"role": "user", "content": "laptop"}])
    assert out["is_ready_to_search"] is False


def test_ready_without_query_uses_users_words(monkeypatch):
    _reply(monkeypatch, {"message": "On it!", "is_ready_to_search": True, "search_query": ""})
    out = chat_agent.process_chat([{"role": "user", "content": "i7 gaming laptop"}])
    assert out == {"message": "On it!", "is_ready_to_search": True, "search_query": "i7 gaming laptop"}


def test_json_wrapped_in_prose_and_fences_is_parsed(monkeypatch):
    _reply(monkeypatch, 'Sure!\n```json\n{"message": "Budget?", "is_ready_to_search": false}\n```')
    out = chat_agent.process_chat([{"role": "user", "content": "shoes"}])
    assert out["message"] == "Budget?"


def test_confirmation_forces_search_with_clean_query(monkeypatch):
    _reply(monkeypatch, {"message": "So, a camera bag?", "is_ready_to_search": False})
    history = [
        {"role": "user", "content": "camera bag for travel"},
        {"role": "agent", "content": "So, you're looking for a camera bag?"},
        {"role": "user", "content": "Yes!"},
    ]
    out = chat_agent.process_chat(history)
    assert out["is_ready_to_search"] is True
    assert out["search_query"] == "camera bag for travel"


def test_too_many_rounds_forces_search(monkeypatch):
    _reply(monkeypatch, {"message": "Any colour?", "is_ready_to_search": False})
    history = []
    for text in ["shoes", "running", "men", "size 9"]:
        history += [{"role": "user", "content": text}, {"role": "agent", "content": "ok?"}]
    out = chat_agent.process_chat(history[:-1])
    assert out["is_ready_to_search"] is True


def test_llm_failure_falls_back_to_search(monkeypatch):
    _reply(monkeypatch, "not json at all")
    out = chat_agent.process_chat([{"role": "user", "content": "bluetooth speaker"}])
    assert out["is_ready_to_search"] is True
    assert out["search_query"] == "bluetooth speaker"


def test_llm_failure_on_greeting_asks_instead_of_searching(monkeypatch):
    _reply(monkeypatch, "not json at all")
    out = chat_agent.process_chat([{"role": "user", "content": "hi"}])
    assert out["is_ready_to_search"] is False


def test_config_error_propagates(monkeypatch):
    def boom(prompt):
        raise LLMConfigError("no key")
    monkeypatch.setattr(chat_agent, "_ask", boom)
    with pytest.raises(LLMConfigError):
        chat_agent.process_chat([{"role": "user", "content": "hi"}])
