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
