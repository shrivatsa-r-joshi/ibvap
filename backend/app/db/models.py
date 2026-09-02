"""
Owner: Backend

Goal
----
SQLite table `events` logging every detection (that has at least one object) and
every alert, so the dashboard/demo can show a history. Schema (docs/schema.md):

  id          INTEGER PRIMARY KEY AUTOINCREMENT
  type        TEXT        -- "detection" | "alert"
  timestamp   TEXT         -- ISO 8601
  object_id   TEXT NULL
  class       TEXT NULL
  payload     TEXT         -- full message as JSON, for anything not worth its own column

Keep this file framework-agnostic (plain sqlite3 or SQLAlchemy — your call) so
main.py can call `log_event(message_dict)` without caring about the internals.
"""
from app import config


def init_db() -> None:
    """Create the events table if it doesn't exist yet."""
    # TODO: implement
    raise NotImplementedError


def log_event(message: dict) -> None:
    """
    Args:
        message: a `detection` or `alert` message dict matching docs/schema.md
    """
    # TODO: implement
    raise NotImplementedError
