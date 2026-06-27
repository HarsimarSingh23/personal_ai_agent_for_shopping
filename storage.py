"""
storage.py — Persistent session storage for the AI Shopping Agent.

Supports both PostgreSQL (production via DATABASE_URL env var)
and SQLite (local development fallback).
"""

import logging
import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, Column, String, DateTime, JSON, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Database URL — PostgreSQL (production) or SQLite (dev fallback)
# ──────────────────────────────────────────────────────────────────────────────
_DATABASE_URL = os.getenv("DATABASE_URL")

if _DATABASE_URL:
    # PostgreSQL — use connection pool
    log.info("Storage: connecting to PostgreSQL")
    engine = create_engine(
        _DATABASE_URL,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,          # detect stale connections
        pool_recycle=300,            # recycle connections every 5 min
        echo=False,
    )
else:
    # SQLite fallback for local development
    _RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(_RESULTS_DIR, exist_ok=True)
    _DB_FILE = os.path.join(_RESULTS_DIR, "sessions.db")
    log.info("Storage: using SQLite fallback at %s", _DB_FILE)
    engine = create_engine(
        f"sqlite:///{_DB_FILE}",
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ──────────────────────────────────────────────────────────────────────────────
# ORM Model
# ──────────────────────────────────────────────────────────────────────────────
class SessionRecord(Base):
    __tablename__ = "sessions"

    session_id     = Column(String, primary_key=True, index=True)
    timestamp      = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    query_original = Column(String, nullable=False)
    query_english  = Column(String, nullable=False)
    results        = Column(JSON, nullable=False)
    recommendation = Column(JSON, nullable=True)


def init_db():
    log.info("Storage: initializing database tables")
    Base.metadata.create_all(bind=engine)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def _to_dict(record: SessionRecord) -> dict:
    return {
        "session_id":     record.session_id,
        "timestamp":      record.timestamp.isoformat() if record.timestamp else None,
        "query_original": record.query_original,
        "query_english":  record.query_english,
        "results":        record.results,
        "recommendation": record.recommendation,
    }


def _get_db():
    """Context-managed DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────
def save_session(
    query_original:  str,
    query_english:   str,
    amazon_results:  list[dict],
    flipkart_results: list[dict],
    recommendation:  dict,
    ddg_results:     list[dict] | None = None,
) -> str:
    """Persist a search session and return its session_id."""
    session_id = str(uuid.uuid4())
    results_json = {
        "amazon":   amazon_results,
        "flipkart": flipkart_results,
        "web":      ddg_results or [],
    }

    db = SessionLocal()
    try:
        record = SessionRecord(
            session_id=session_id,
            query_original=query_original,
            query_english=query_english,
            results=results_json,
            recommendation=recommendation,
        )
        db.add(record)
        db.commit()
        log.info("Session saved: %s", session_id)
        return session_id
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def load_sessions() -> list[dict]:
    """Return all saved sessions, newest first."""
    db = SessionLocal()
    try:
        records = (
            db.query(SessionRecord)
            .order_by(SessionRecord.timestamp.desc())
            .all()
        )
        return [_to_dict(r) for r in records]
    finally:
        db.close()


def load_last_session() -> dict | None:
    """Return the most recent session, or None."""
    db = SessionLocal()
    try:
        record = (
            db.query(SessionRecord)
            .order_by(SessionRecord.timestamp.desc())
            .first()
        )
        return _to_dict(record) if record else None
    finally:
        db.close()


def load_session_by_id(session_id: str) -> dict | None:
    """Return a single session by ID, or None if not found."""
    db = SessionLocal()
    try:
        record = db.query(SessionRecord).filter(
            SessionRecord.session_id == session_id
        ).first()
        return _to_dict(record) if record else None
    finally:
        db.close()


def check_db_connection() -> bool:
    """Verify the database is reachable. Used by /health endpoint."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        log.error("DB health check failed: %s", e)
        return False
