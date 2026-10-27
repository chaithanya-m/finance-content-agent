"""
SQLite database layer for storing generated DialogueScript records.

Schema
------
scripts
  id            INTEGER PRIMARY KEY AUTOINCREMENT
  topic         TEXT NOT NULL
  generated_at  TEXT NOT NULL  (ISO-8601)
  status        TEXT NOT NULL  (pending | ready | published | failed)
  carousel_json TEXT NOT NULL  (full JSON blob)
  video_json    TEXT NOT NULL  (full JSON blob — same DialogueScript, same data)
  verified_facts TEXT NOT NULL (JSON array of fact strings)
  sources       TEXT NOT NULL  (JSON array of URL strings)
  output_dir    TEXT           (filesystem path of the draft bundle, if saved)
  error         TEXT           (error message if status=failed)

topics_history
  id            INTEGER PRIMARY KEY AUTOINCREMENT
  topic         TEXT NOT NULL
  generated_at  TEXT NOT NULL
  script_id     INTEGER REFERENCES scripts(id)

Usage
-----
    from src.db import ScriptDatabase
    db = ScriptDatabase()                    # uses data/scripts.db by default
    db.save(script, output_dir="output/...")
    rows = db.list_all()
    row  = db.get_by_id(3)
    db.mark_published(script_id=3)
"""

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .dialogue_script import DialogueScript


_DEFAULT_DB = Path("data/scripts.db")

_DDL = """
CREATE TABLE IF NOT EXISTS scripts (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    topic          TEXT    NOT NULL,
    generated_at   TEXT    NOT NULL,
    status         TEXT    NOT NULL DEFAULT 'ready',
    carousel_json  TEXT    NOT NULL,
    video_json     TEXT    NOT NULL,
    verified_facts TEXT    NOT NULL,
    sources        TEXT    NOT NULL,
    output_dir     TEXT,
    error          TEXT
);

CREATE TABLE IF NOT EXISTS topics_history (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    topic          TEXT    NOT NULL,
    generated_at   TEXT    NOT NULL,
    script_id      INTEGER REFERENCES scripts(id)
);
"""


class ScriptDatabase:
    """Thin SQLite wrapper for dialogue scripts."""

    def __init__(self, db_path: Path = _DEFAULT_DB) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_schema()

    # ── Setup ─────────────────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(_DDL)

    # ── Write ─────────────────────────────────────────────────────────────────

    def save(
        self,
        script: DialogueScript,
        output_dir: str | None = None,
        status: str = "ready",
    ) -> int:
        """
        Persist a DialogueScript to the database.

        Returns the new row id (script_id).
        """
        now = datetime.now(tz=timezone.utc).isoformat()
        data = asdict(script)
        carousel_json = json.dumps(data, ensure_ascii=False)
        # video and carousel share the same DialogueScript blob;
        # they are stored separately so callers can query either format
        video_json = carousel_json

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO scripts
                    (topic, generated_at, status, carousel_json, video_json,
                     verified_facts, sources, output_dir)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    script.topic,
                    now,
                    status,
                    carousel_json,
                    video_json,
                    json.dumps(script.verified_facts, ensure_ascii=False),
                    json.dumps(script.sources, ensure_ascii=False),
                    output_dir,
                ),
            )
            script_id = cursor.lastrowid

            conn.execute(
                """
                INSERT INTO topics_history (topic, generated_at, script_id)
                VALUES (?, ?, ?)
                """,
                (script.topic, now, script_id),
            )

        return script_id

    def save_error(self, topic: str, error: str) -> int:
        """Record a failed generation attempt."""
        now = datetime.now(tz=timezone.utc).isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO scripts
                    (topic, generated_at, status, carousel_json, video_json,
                     verified_facts, sources, error)
                VALUES (?, ?, 'failed', '{}', '{}', '[]', '[]', ?)
                """,
                (topic, now, error),
            )
            script_id = cursor.lastrowid
            conn.execute(
                """
                INSERT INTO topics_history (topic, generated_at, script_id)
                VALUES (?, ?, ?)
                """,
                (topic, now, script_id),
            )
        return script_id

    def mark_published(self, script_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE scripts SET status='published' WHERE id=?",
                (script_id,),
            )

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_by_id(self, script_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM scripts WHERE id=?", (script_id,)
            ).fetchone()
        return dict(row) if row else None

    def list_all(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, topic, generated_at, status, output_dir, error "
                "FROM scripts ORDER BY generated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def topics_generated(self) -> set[str]:
        """Return the set of topic titles that have been successfully generated."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT topic FROM scripts WHERE status != 'failed'"
            ).fetchall()
        return {row["topic"] for row in rows}

    def get_carousel_json(self, script_id: int) -> dict[str, Any] | None:
        row = self.get_by_id(script_id)
        if row is None or row.get("status") == "failed":
            return None
        return json.loads(row["carousel_json"])

    def get_video_json(self, script_id: int) -> dict[str, Any] | None:
        row = self.get_by_id(script_id)
        if row is None or row.get("status") == "failed":
            return None
        return json.loads(row["video_json"])

