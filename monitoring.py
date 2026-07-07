"""
monitoring.py — AgentMonitor (contextdb) integration for the AI Shopping Agent.

AgentMonitor is an in-memory observability DB for LLM agents. This module wires
it into the backend so every /api/search run becomes a monitored "session":
the user query, each scraper tool-call (args, results, latency, errors), and the
LLM recommendation are recorded and streamed to a live dashboard.

    Dashboard:  http://127.0.0.1:8765   (started at API startup)
    Repo:       https://github.com/HarsimarSingh23/AgentMonitor

Everything here degrades gracefully: if `contextdb` isn't installed, or
AGENT_MONITOR=0, the wrappers become no-ops and the app runs unchanged.

Env vars:
    AGENT_MONITOR        "0" to disable entirely (default: enabled)
    AGENT_MONITOR_PORT   dashboard port (default: 8765)
    AGENT_MONITOR_OPEN   "1" to auto-open a browser tab (default: off — headless)
"""

import logging
import os
from contextlib import contextmanager

log = logging.getLogger(__name__)

try:
    import contextdb as cdb
except ImportError:  # package not installed — run without monitoring
    cdb = None

_ENABLED = cdb is not None and os.getenv("AGENT_MONITOR", "1") != "0"
_dashboard_started = False


def enabled() -> bool:
    return _ENABLED


def start_dashboard() -> None:
    """Start the live dashboard once (non-blocking, daemon thread)."""
    global _dashboard_started
    if not _ENABLED or _dashboard_started:
        return
    port = int(os.getenv("AGENT_MONITOR_PORT", "8765"))
    open_browser = os.getenv("AGENT_MONITOR_OPEN", "0") == "1"
    try:
        cdb.serve(port=port, host="127.0.0.1", open_browser=open_browser, block=False)
        _dashboard_started = True
        log.info("📊 AgentMonitor dashboard live at http://127.0.0.1:%d", port)
    except Exception as e:  # a taken port shouldn't kill the API
        log.warning("AgentMonitor dashboard failed to start: %s", e)


def tool(fn, name: str | None = None):
    """Wrap a callable so every call is recorded (args, result, latency, errors).

    Returns `fn` unchanged when monitoring is disabled.
    """
    if not _ENABLED:
        return fn
    return cdb.log_tool(name=name or getattr(fn, "__name__", "tool"))(fn)


class _NullSession:
    """No-op stand-in for a contextdb Session when monitoring is disabled."""

    id = None

    def log_user_message(self, *a, **k): ...
    def log_response(self, *a, **k): ...
    def log_thinking(self, *a, **k): ...
    def log_context(self, *a, **k): ...

    @contextmanager
    def turn(self, label: str = "turn"):
        yield None


@contextmanager
def session(**metadata):
    """Open a monitored session, or a no-op session if monitoring is disabled."""
    if not _ENABLED:
        yield _NullSession()
        return
    with cdb.session(**metadata) as s:
        yield s
