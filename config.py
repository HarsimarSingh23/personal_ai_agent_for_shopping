"""
config.py — Centralised runtime configuration for the AI Shopping Agent API.

Every setting is read from the environment (a local `.env` is loaded first),
so the same image runs in development, CI and production. See `.env.example`
for the full list with descriptions.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _str(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _list(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


@dataclass
class Settings:
    # ── App ──────────────────────────────────────────────────────────────────
    app_env: str = "development"            # development | production
    app_version: str = "1.1.0"
    log_level: str = "INFO"
    log_format: str = "text"                # text | json
    enable_docs: bool = True                # /docs and /openapi.json

    # ── HTTP / security ─────────────────────────────────────────────────────
    allowed_origins: list[str] = field(default_factory=lambda: ["*"])
    api_key: str = ""                       # when set, /api/* requires X-API-Key
    rate_limit_search_per_min: int = 10     # per client IP, 0 disables
    rate_limit_chat_per_min: int = 30
    rate_limit_read_per_min: int = 120

    # ── Agent ───────────────────────────────────────────────────────────────
    scrape_timeout_seconds: int = 45
    scraper_workers: int = 16
    max_chat_messages: int = 30             # older turns are dropped from the prompt
    max_message_chars: int = 2000

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @classmethod
    def from_env(cls) -> "Settings":
        app_env = _str("APP_ENV", "development").lower()
        is_prod = app_env == "production"
        return cls(
            app_env=app_env,
            app_version=_str("APP_VERSION", "1.1.0"),
            log_level=_str("LOG_LEVEL", "INFO").upper(),
            log_format=_str("LOG_FORMAT", "json" if is_prod else "text").lower(),
            enable_docs=_bool("ENABLE_DOCS", not is_prod),
            allowed_origins=_list("ALLOWED_ORIGINS", "*"),
            api_key=_str("API_KEY"),
            rate_limit_search_per_min=_int("RATE_LIMIT_SEARCH_PER_MIN", 10),
            rate_limit_chat_per_min=_int("RATE_LIMIT_CHAT_PER_MIN", 30),
            rate_limit_read_per_min=_int("RATE_LIMIT_READ_PER_MIN", 120),
            scrape_timeout_seconds=_int("SCRAPE_TIMEOUT_SECONDS", 45),
            scraper_workers=_int("SCRAPER_WORKERS", 16),
            max_chat_messages=_int("MAX_CHAT_MESSAGES", 30),
            max_message_chars=_int("MAX_MESSAGE_CHARS", 2000),
        )


settings = Settings.from_env()
