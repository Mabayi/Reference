"""综述存储 CRUD"""
import sqlite3
import json
from pathlib import Path
from config.settings import settings, BASE_DIR

_db_relative = settings.DATABASE_URL.replace("sqlite:///", "")
DB_PATH = BASE_DIR / _db_relative


def _get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_surveys_table():
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS surveys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                topic TEXT,
                paper_ids TEXT,
                content TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def create_survey(user_id: int, topic: str, paper_ids: list, content: str) -> int:
    with _get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO surveys (user_id, topic, paper_ids, content) VALUES (?, ?, ?, ?)",
            (user_id, topic, json.dumps(paper_ids), content),
        )
        conn.commit()
        return cursor.lastrowid


def get_surveys_by_user(user_id: int) -> list:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT id, topic, paper_ids, created_at FROM surveys WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_survey_by_id(survey_id: int, user_id: int) -> dict | None:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM surveys WHERE id = ? AND user_id = ?", (survey_id, user_id)
        ).fetchone()
        return dict(row) if row else None
