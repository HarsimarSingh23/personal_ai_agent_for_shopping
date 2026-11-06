"""
storage.py — Session persistence (PostgreSQL in production, SQLite locally).

Each search is stored as one row. Rows carry an optional `client_id` (an
anonymous per-install ID sent by the app in `X-Client-ID`) so that a device
only ever sees and deletes its own history.
"""

import logging
import os
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import JSON, Column, DateTime, Index, String, create_engine, inspect, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

load_dotenv()

log = logging.getLogger(__name__)

engine = None          # type: ignore[assignment]
SessionLocal = None    # type: ignore[assignment]
Base = declarative_base()


class SessionRecord(Base):
    __tablename__ = "sessions"

    session_id     = Column(String, primary_key=True, index=True)
    timestamp      = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    client_id      = Column(String(64), nullable=True)
    query_original = Column(String, nullable=False)
    query_english  = Column(String, nullable=False)
    results        = Column(JSON, nullable=False)
    recommendation = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_sessions_client_ts", "client_id", "timestamp"),
    )


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        # Heroku/Render style URLs use the deprecated "postgres://" scheme.
        return url.replace("postgres://", "postgresql://", 1)
    results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(results_dir, exist_ok=True)
    return f"sqlite:///{os.path.join(results_dir, 'sessions.db')}"


def _migrate() -> None:
    """Add columns introduced after the first release to existing tables."""
    columns = {c["name"] for c in inspect(engine).get_columns("sessions")}
    with engine.begin() as conn:
        if "client_id" not in columns:
            log.info("Storage: migrating — adding sessions.client_id")
            conn.execute(text("ALTER TABLE sessions ADD COLUMN client_id VARCHAR(64)"))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_sessions_client_ts ON sessions (client_id, timestamp)"
            ))


def init_db() -> None:
    global engine, SessionLocal

    url = _database_url()
    if url.startswith("sqlite"):
        log.info("Storage: using SQLite at %s", url.removeprefix("sqlite:///"))
        engine = create_engine(url, connect_args={"check_same_thread": False}, poolclass=NullPool)
    else:
        log.info("Storage: connecting to PostgreSQL")
        engine = create_engine(
            url,
            pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
            pool_pre_ping=True,
            pool_recycle=300,
        )

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    _migrate()


def _require_db() -> Session:
    if SessionLocal is None:
        raise RuntimeError("Database not initialised. Call storage.init_db() at startup.")
    return SessionLocal()


def _counts(results: dict | None) -> dict:
    results = results or {}
    return {k: len(results.get(k) or []) for k in ("amazon", "flipkart", "web")}


def _to_dict(record: SessionRecord, summary: bool = False) -> dict:
    data = {
        "session_id":     record.session_id,
        "timestamp":      record.timestamp.isoformat() if record.timestamp else None,
        "query_original": record.query_original,
        "query_english":  record.query_english,
        "recommendation": record.recommendation,
        "result_counts":  _counts(record.results),
    }
    if not summary:
        data["results"] = record.results
    return data


def _owned_by(query, client_id: str | None):
    if client_id:
        return query.filter(SessionRecord.client_id == client_id)
    # Legacy clients without an ID only see rows that were saved without one.
    return query.filter(SessionRecord.client_id.is_(None))


def save_session(
    query_original:   str,
    query_english:    str,
    amazon_results:   list[dict],
    flipkart_results: list[dict],
    recommendation:   dict | None,
    ddg_results:      list[dict] | None = None,
    client_id:        str | None = None,
) -> str:
    session_id = str(uuid.uuid4())
    record = SessionRecord(
        session_id=session_id,
        client_id=client_id,
        query_original=query_original,
        query_english=query_english,
        results={"amazon": amazon_results, "flipkart": flipkart_results, "web": ddg_results or []},
        recommendation=recommendation,
    )
    db = _require_db()
    try:
        db.add(record)
        db.commit()
        return session_id
    except Exception:
        db.rollback()
        log.error("Failed to save session — rolled back", exc_info=True)
        raise
    finally:
        db.close()


def load_sessions(
    limit: int = 50,
    offset: int = 0,
    client_id: str | None = None,
    summary: bool = False,
) -> list[dict]:
    db = _require_db()
    try:
        records = (
            _owned_by(db.query(SessionRecord), client_id)
            .order_by(SessionRecord.timestamp.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [_to_dict(r, summary=summary) for r in records]
    finally:
        db.close()


def load_last_session(client_id: str | None = None) -> dict | None:
    sessions = load_sessions(limit=1, client_id=client_id)
    return sessions[0] if sessions else None


def load_session_by_id(session_id: str, client_id: str | None = None) -> dict | None:
    db = _require_db()
    try:
        record = db.get(SessionRecord, session_id)
        if record is None:
            return None
        # Rows owned by a device are private to it; legacy rows stay readable by ID.
        if record.client_id and record.client_id != client_id:
            return None
        return _to_dict(record)
    finally:
        db.close()


def delete_session(session_id: str, client_id: str | None) -> bool:
    db = _require_db()
    try:
        record = db.get(SessionRecord, session_id)
        if record is None or record.client_id != client_id:
            return False
        db.delete(record)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def delete_sessions_for_client(client_id: str) -> int:
    db = _require_db()
    try:
        count = (
            db.query(SessionRecord)
            .filter(SessionRecord.client_id == client_id)
            .delete(synchronize_session=False)
        )
        db.commit()
        return count
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_db_connection() -> bool:
    if engine is None:
        return False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        log.error("DB health check failed: %s", e)
        return False
