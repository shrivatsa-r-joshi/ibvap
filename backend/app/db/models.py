"""
Owner: Backend

SQLite event log. Persists every detection (with objects) and every alert
so the dashboard can show history. Schema matches docs/schema.md § 3.
"""
import json
import sqlite3
import logging
from app import config

logger = logging.getLogger("ibvap.db")

_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    """Return (and cache) the SQLite connection."""
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(config.DATABASE_PATH, check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL")  # safer for concurrent reads
    return _conn


def init_db() -> None:
    """Create the events table if it doesn't exist yet."""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            type        TEXT NOT NULL,
            timestamp   TEXT NOT NULL,
            object_id   TEXT,
            class       TEXT,
            payload     TEXT NOT NULL
        )
    """)
    conn.commit()
    logger.info(f"Database initialized at {config.DATABASE_PATH}")


def log_event(message: dict) -> None:
    """
    Log a detection or alert message to the events table.

    For detection messages: logs one row per detection event (full object list in payload).
    For alert messages: logs a single row with object_id and class extracted.
    Skips detection messages with zero objects (don't flood the DB with empty frames).
    """
    msg_type = message.get("type")
    timestamp = message.get("timestamp", "")
    payload = json.dumps(message)

    conn = _get_conn()

    if msg_type == "alert":
        conn.execute(
            "INSERT INTO events (type, timestamp, object_id, class, payload) VALUES (?, ?, ?, ?, ?)",
            (msg_type, timestamp, message.get("object_id"), message.get("class"), payload),
        )
        conn.commit()
        logger.info(f"Logged alert: {message.get('alert_id')}")

    elif msg_type == "detection":
        objects = message.get("objects", [])
        if not objects:
            return  # schema says: don't log empty frames
        # Log one row per detection event — the full object list is in payload
        conn.execute(
            "INSERT INTO events (type, timestamp, object_id, class, payload) VALUES (?, ?, ?, ?, ?)",
            (msg_type, timestamp, None, None, payload),
        )
        conn.commit()
        logger.debug(f"Logged detection frame_id={message.get('frame_id')} with {len(objects)} objects")
