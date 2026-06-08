"""
storage.py — Persistent session storage for the AI Shopping Agent.

Each search is saved as a session in results/sessions.json (append-only log).

    from storage import save_session, load_sessions
"""

import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone

log = logging.getLogger(__name__)

_RESULTS_DIR  = os.path.join(os.path.dirname(__file__), "results")
_SESSION_FILE = os.path.join(_RESULTS_DIR, "sessions.json")
_WRITE_LOCK   = threading.Lock()  # serialise concurrent writes
MAX_SESSIONS  = 500               # trim oldest sessions beyond this cap


def _ensure_dir() -> None:
    os.makedirs(_RESULTS_DIR, exist_ok=True)


def _load_raw() -> list[dict]:
    if not os.path.exists(_SESSION_FILE):
        return []
    with open(_SESSION_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            log.warning("sessions.json is corrupt — starting fresh.")
            return []


def save_session(
    query_original: str,
    query_english: str,
    amazon_results: list[dict],
    flipkart_results: list[dict],
    recommendation: dict,
    ddg_results: list[dict] | None = None,
) -> str:
    """
    Save a search session to disk. Returns the assigned session_id (UUID4).
    """
    _ensure_dir()
    with _WRITE_LOCK:
        sessions = _load_raw()

        session = {
            "session_id":     str(uuid.uuid4()),
            "timestamp":      datetime.now(timezone.utc).isoformat(),
            "query_original": query_original,
            "query_english":  query_english,
            "results": {
                "amazon":   [dict(p, source="amazon")   for p in amazon_results],
                "flipkart": [dict(p, source="flipkart") for p in flipkart_results],
                "web":      ddg_results or [],
            },
            "recommendation": recommendation,
        }

        sessions.append(session)

        if len(sessions) > MAX_SESSIONS:
            sessions = sessions[-MAX_SESSIONS:]
            log.info("Session cap reached (%d); oldest sessions trimmed.", MAX_SESSIONS)

        with open(_SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(sessions, f, indent=2, ensure_ascii=False)

    log.info("Session saved: %s (%s)", session["session_id"], _SESSION_FILE)
    return session["session_id"]


def load_sessions() -> list[dict]:
    """Return all saved sessions (newest last)."""
    return _load_raw()


def load_last_session() -> dict | None:
    """Return the most recent session, or None if no sessions exist."""
    sessions = _load_raw()
    return sessions[-1] if sessions else None
