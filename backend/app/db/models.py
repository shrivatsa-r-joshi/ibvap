"""
Owner: Backend

SQLite storage for logging `detection` and `alert` messages (docs/schema.md).
Table: events
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from app import config

logger = logging.getLogger("ibvap.db")


def get_db_connection() -> sqlite3.Connection:
    """Creates a connection to the SQLite database, ensuring directories exist."""
    db_path = getattr(config, "DATABASE_PATH", "backend/app/db/events.db")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the events table if it does not exist yet."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    object_id TEXT,
                    class TEXT,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)")
        logger.info("Database initialized at %s", getattr(config, "DATABASE_PATH", "backend/app/db/events.db"))
    finally:
        conn.close()


def log_event(message: Dict[str, Any]) -> None:
    """
    Logs a detection or alert message to the events table.
    Per docs/schema.md:
      - Detection: logged when it has at least one object
      - Alert: logged on every crossing
    """
    msg_type = message.get("type", "unknown")
    timestamp = message.get("timestamp", "")
    payload = json.dumps(message)

    object_id: Optional[str] = None
    obj_class: Optional[str] = None

    if msg_type == "alert":
        object_id = message.get("object_id")
        obj_class = message.get("class")
    elif msg_type == "detection":
        objects = message.get("objects", [])
        if not objects:
            return  # Don't flood DB with empty frames
        # Extract first object id and class as summary, full array in payload
        object_id = objects[0].get("id")
        obj_class = objects[0].get("class")

    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO events (type, timestamp, object_id, class, payload)
                VALUES (?, ?, ?, ?, ?)
                """,
                (msg_type, timestamp, object_id, obj_class, payload),
            )
    except Exception as e:
        logger.error("Failed to log event to DB: %s", e)
    finally:
        conn.close()


def get_recent_events(limit: int = 50, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves recent events from SQLite for dashboard history display."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if event_type:
            cursor.execute(
                "SELECT id, type, timestamp, object_id, class, payload FROM events WHERE type = ? ORDER BY id DESC LIMIT ?",
                (event_type, limit),
            )
        else:
            cursor.execute(
                "SELECT id, type, timestamp, object_id, class, payload FROM events ORDER BY id DESC LIMIT ?",
                (limit,),
            )
        rows = cursor.fetchall()
        events = []
        for r in rows:
            events.append({
                "id": r["id"],
                "type": r["type"],
                "timestamp": r["timestamp"],
                "object_id": r["object_id"],
                "class": r["class"],
                "payload": json.loads(r["payload"]) if r["payload"] else {},
            })
        return events
    finally:
        conn.close()
