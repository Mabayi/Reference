"""文献阅读 - 批注和高亮存储"""
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


def init_annotations_table():
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS annotations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                paper_id INTEGER NOT NULL,
                type TEXT NOT NULL DEFAULT 'highlight',
                text TEXT NOT NULL,
                note TEXT DEFAULT '',
                color TEXT DEFAULT '#ffeb3b',
                page_index INTEGER DEFAULT 0,
                char_start INTEGER DEFAULT 0,
                char_end INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(annotations)").fetchall()}
        if "selector_json" not in columns:
            conn.execute("ALTER TABLE annotations ADD COLUMN selector_json TEXT DEFAULT ''")
        # 用户翻译配额表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS translate_quota (
                user_id INTEGER PRIMARY KEY,
                free_papers_used INTEGER DEFAULT 0
            )
        """)
        conn.commit()


def add_annotation(user_id: int, paper_id: int, type: str, text: str, note: str = "",
                   color: str = "#ffeb3b", page_index: int = 0, char_start: int = 0, char_end: int = 0,
                   selector_json: str = "") -> int:
    with _get_conn() as conn:
        cursor = conn.execute(
            """INSERT INTO annotations (user_id, paper_id, type, text, note, color, page_index, char_start, char_end, selector_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, paper_id, type, text, note, color, page_index, char_start, char_end, selector_json)
        )
        conn.commit()
        return cursor.lastrowid


def get_annotations(user_id: int, paper_id: int) -> list:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM annotations WHERE user_id = ? AND paper_id = ? ORDER BY page_index, char_start",
            (user_id, paper_id)
        ).fetchall()
        return [dict(r) for r in rows]


def delete_annotation(annotation_id: int, user_id: int) -> bool:
    with _get_conn() as conn:
        cursor = conn.execute(
            "DELETE FROM annotations WHERE id = ? AND user_id = ?", (annotation_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0


def get_free_papers_used(user_id: int) -> int:
    with _get_conn() as conn:
        row = conn.execute("SELECT free_papers_used FROM translate_quota WHERE user_id = ?", (user_id,)).fetchone()
        return row["free_papers_used"] if row else 0


def use_free_translate(user_id: int):
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO translate_quota (user_id, free_papers_used) VALUES (?, 1) ON CONFLICT(user_id) DO UPDATE SET free_papers_used = free_papers_used + 1",
            (user_id,)
        )
        conn.commit()
