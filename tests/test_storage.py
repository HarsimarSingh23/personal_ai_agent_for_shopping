import pytest

import sqlite3

from sqlalchemy import inspect

import storage


def test_init_db_migrates_legacy_table(tmp_path, monkeypatch):
    db_file = tmp_path / "legacy.db"
    con = sqlite3.connect(db_file)
    con.execute(
        "CREATE TABLE sessions (session_id VARCHAR PRIMARY KEY, timestamp DATETIME NOT NULL, "
        "query_original VARCHAR NOT NULL, query_english VARCHAR NOT NULL, results JSON NOT NULL, "
        "recommendation JSON)"
    )
    con.execute(
        "INSERT INTO sessions VALUES ('11111111-1111-1111-1111-111111111111', '2026-01-01 00:00:00', "
        "'old', 'old', '{\"amazon\": [], \"flipkart\": [], \"web\": []}', NULL)"
    )
    con.commit()
    con.close()

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file.as_posix()}")
    storage.init_db()

    columns = {c["name"] for c in inspect(storage.engine).get_columns("sessions")}
    assert "client_id" in columns
    # Legacy rows have no owner, so they stay visible to clients without an ID.
    assert [s["query_original"] for s in storage.load_sessions()] == ["old"]
    assert storage.load_sessions(client_id="device-aaaaaaaa") == []

    storage.init_db()  # idempotent


@pytest.mark.parametrize("raw, expected", [
    ("postgresql://u:p@db:5432/shop", "postgresql+psycopg2://u:p@db:5432/shop"),
    ("postgres://u:p@db:5432/shop", "postgresql+psycopg2://u:p@db:5432/shop"),
    ("postgresql+psycopg://u:p@db/shop", "postgresql+psycopg://u:p@db/shop"),   # explicit driver kept
    ("sqlite:////tmp/x.db", "sqlite:////tmp/x.db"),
])
def test_database_url_names_the_installed_postgres_driver(monkeypatch, raw, expected):
    """SQLAlchemy 2.1 defaults "postgresql://" to psycopg 3, which we don't install."""
    import storage
    monkeypatch.setenv("DATABASE_URL", raw)
    assert storage._database_url() == expected
