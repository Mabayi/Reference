import json
import sqlite3

from config.settings import BASE_DIR, settings

_db_relative = settings.DATABASE_URL.replace("sqlite:///", "")
DB_PATH = BASE_DIR / _db_relative


def _get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_experiments_table() -> None:
    with _get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                goal TEXT NOT NULL,
                hypothesis TEXT DEFAULT '',
                content_json TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def create_experiment(user_id: int, goal: str, hypothesis: str, content: dict) -> int:
    with _get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO experiments (user_id, goal, hypothesis, content_json) VALUES (?, ?, ?, ?)",
            (user_id, goal, hypothesis, json.dumps(content, ensure_ascii=False)),
        )
        conn.commit()
        return cursor.lastrowid


def list_experiments(user_id: int, limit: int = 20) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM experiments WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()

    results: list[dict] = []
    for row in rows:
        item = dict(row)
        try:
            item["content"] = json.loads(item["content_json"])
        except (json.JSONDecodeError, TypeError):
            item["content"] = {}
        results.append(item)
    return results


def count_experiments(user_id: int) -> int:
    with _get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) AS total FROM experiments WHERE user_id = ?", (user_id,)).fetchone()
        return int(row["total"])

