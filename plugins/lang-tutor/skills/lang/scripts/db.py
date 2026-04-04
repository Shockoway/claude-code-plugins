"""SQLite database layer for lang-tutor."""

import sqlite3
import os
from pathlib import Path


def get_db_path() -> Path:
    return Path(os.environ.get("LANG_DB", "./lang.db"))


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Initialize schema. Safe to call multiple times."""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            language TEXT NOT NULL,
            level_cefr TEXT NOT NULL,
            goal TEXT NOT NULL,
            target_level TEXT NOT NULL,
            daily_minutes INTEGER NOT NULL DEFAULT 30,
            schedule_json TEXT NOT NULL DEFAULT '{}',
            onboarded_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS topics (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            cefr_milestone TEXT,
            strand TEXT,
            prerequisites_json TEXT NOT NULL DEFAULT '[]',
            mastery_prob REAL NOT NULL DEFAULT 0.0,
            last_practiced TEXT,
            priority INTEGER NOT NULL DEFAULT 5
        );

        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id TEXT NOT NULL REFERENCES topics(id),
            content TEXT NOT NULL,
            item_type TEXT NOT NULL,
            due_at TEXT,
            interval_days REAL NOT NULL DEFAULT 1.0,
            ease_factor REAL NOT NULL DEFAULT 2.5
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            duration_s INTEGER,
            topics_json TEXT NOT NULL DEFAULT '[]',
            adherence_planned INTEGER DEFAULT 0,
            adherence_actual INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER REFERENCES items(id),
            topic_id TEXT NOT NULL REFERENCES topics(id),
            session_id INTEGER REFERENCES sessions(id),
            ts TEXT NOT NULL,
            score REAL NOT NULL,
            latency_ms INTEGER,
            exercise_type TEXT NOT NULL,
            error_type TEXT,
            error_context TEXT
        );
    """)
    conn.commit()
    conn.close()
