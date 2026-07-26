
import logging
import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, Column, String, DateTime, JSON, Integer, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import NullPool, QueuePool
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)


engine = None          # type: ignore[assignment]
SessionLocal = None    # type: ignore[assignment]
Base = declarative_base()

_DATABASE_URL = os.getenv("DATABASE_URL")



class SessionRecord(Base):
    __tablename__ = "sessions"

    session_id     = Column(String, primary_key=True, index=True)

    timestamp      = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        nullable=False,
    )
    query_original = Column(String, nullable=False)
    query_english  = Column(String, nullable=False)
    results        = Column(JSON, nullable=False)
    recommendation = Column(JSON, nullable=True)



def init_db() -> None:

    global engine, SessionLocal

    if _DATABASE_URL:
        log.info("Storage: connecting to PostgreSQL")
        engine = create_engine(
            _DATABASE_URL,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=False,
        )
    else:
        _results_dir = os.path.join(os.path.dirname(__file__), "results")
        os.makedirs(_results_dir, exist_ok=True)
        _db_file = os.path.join(_results_dir, "sessions.db")
        log.info("Storage: using SQLite fallback at %s", _db_file)
        engine = create_engine(
            f"sqlite:///{_db_file}",
            connect_args={"check_same_thread": False},
            poolclass=NullPool,
        )

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    log.info("Storage: initializing database tables")
    Base.metadata.create_all(bind=engine)



def _require_db() -> Session:
    if SessionLocal is None:
        raise RuntimeError(
            "Database not initialised. Call storage.init_db() at application startup."
        )
    return SessionLocal()


def _to_dict(record: SessionRecord) -> dict:
    return {
        "session_id":     record.session_id,
        "timestamp":      record.timestamp.isoformat() if record.timestamp else None,
        "query_original": record.query_original,
        "query_english":  record.query_english,
        "results":        record.results,
        "recommendation": record.recommendation,
    }



def save_session(
    query_original:   str,
    query_english:    str,
    amazon_results:   list[dict],
    flipkart_results: list[dict],
    recommendation:   dict,
    ddg_results:      list[dict] | None = None,
) -> str:
    session_id = str(uuid.uuid4())
    results_json = {
        "amazon":   amazon_results,
        "flipkart": flipkart_results,
        "web":      ddg_results or [],
    }

    db = _require_db()
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
        log.error("Failed to save session — rolled back", exc_info=True)
        raise
    finally:
        db.close()


def load_sessions(limit: int = 100) -> list[dict]:
    db = _require_db()
    try:
        records = (
            db.query(SessionRecord)
            .order_by(SessionRecord.timestamp.desc())
            .limit(limit)
            .all()
        )
        return [_to_dict(r) for r in records]
    finally:
        db.close()


def load_last_session() -> dict | None:
    db = _require_db()
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
    db = _require_db()
    try:
        record = db.query(SessionRecord).filter(
            SessionRecord.session_id == session_id
        ).first()
        return _to_dict(record) if record else None
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
