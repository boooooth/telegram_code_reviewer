import sqlite3
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from reviewbot.config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS episodic_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    source TEXT,
    source_ref TEXT,
    input TEXT,
    output TEXT
)
"""

_INDEX = """
CREATE INDEX IF NOT EXISTS idx_episodic_events_chat_id
ON episodic_events (chat_id, created_at)
"""


@lru_cache(maxsize=1)
def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.episodic_db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(_SCHEMA)
    conn.execute(_INDEX)
    return conn


def log_event(chat_id: int, source: str, source_ref: str | None, input_text: str, output_text: str) -> None:
    conn = _connect()
    with conn:
        conn.execute(
            "INSERT INTO episodic_events (chat_id, created_at, source, source_ref, input, output) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (chat_id, datetime.now(timezone.utc).isoformat(), source, source_ref, input_text, output_text),
        )


def recent_events(chat_id: int, limit: int = 3) -> list[dict]:
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM episodic_events WHERE chat_id = ? ORDER BY created_at DESC LIMIT ?",
        (chat_id, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def count_events(chat_id: int) -> int:
    conn = _connect()
    row = conn.execute(
        "SELECT COUNT(*) FROM episodic_events WHERE chat_id = ?", (chat_id,)
    ).fetchone()
    return row[0]


def delete_events_older_than(chat_id: int, days: int) -> int:
    conn = _connect()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with conn:
        cursor = conn.execute(
            "DELETE FROM episodic_events WHERE chat_id = ? AND created_at < ?", (chat_id, cutoff)
        )
    return cursor.rowcount
