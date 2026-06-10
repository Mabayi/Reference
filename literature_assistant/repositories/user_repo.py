import sqlite3
from pathlib import Path
from config.settings import settings, BASE_DIR

# 解析数据库路径：sqlite:///instance/literature.db -> BASE_DIR/instance/literature.db
_db_relative = settings.DATABASE_URL.replace("sqlite:///", "")
DB_PATH = BASE_DIR / _db_relative


def is_admin_username(username: str | None) -> bool:
    """只有 admin 用户名对应系统管理员。"""
    return (username or "").strip() == "admin"


def _get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """创建 users 表，表已存在则跳过"""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                is_disabled INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME
            )
        """)
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "is_admin" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
        if "is_disabled" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN is_disabled INTEGER DEFAULT 0")

        conn.execute(
            """
            UPDATE users
            SET is_admin = CASE WHEN username = 'admin' THEN 1 ELSE 0 END,
                is_disabled = CASE WHEN username = 'admin' THEN 0 ELSE COALESCE(is_disabled, 0) END
            """
        )
        conn.commit()


def create_user(username: str, email: str, password_hash: str) -> dict:
    """创建用户，返回用户字典"""
    with _get_conn() as conn:
        is_admin = 1 if is_admin_username(username) else 0
        cursor = conn.execute(
            "INSERT INTO users (username, email, password_hash, is_admin) VALUES (?, ?, ?, ?)",
            (username, email, password_hash, is_admin),
        )
        conn.commit()
        return get_user_by_id(cursor.lastrowid)


def get_user_by_email(email: str) -> dict | None:
    """按邮箱查找用户"""
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None


def get_user_by_username(username: str) -> dict | None:
    """按用户名查找用户"""
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None


def get_user_by_identifier(identifier: str) -> dict | None:
    """按用户名或邮箱查找用户"""
    value = identifier.strip()
    if not value:
        return None
    with _get_conn() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM users
            WHERE username = ? OR email = ?
            ORDER BY CASE WHEN username = ? THEN 0 ELSE 1 END
            LIMIT 1
            """,
            (value, value, value),
        ).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    """按 ID 查找用户"""
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def update_last_login(user_id: int):
    """更新最后登录时间"""
    with _get_conn() as conn:
        conn.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
            (user_id,),
        )
        conn.commit()


def set_user_disabled(user_id: int, disabled: bool) -> bool:
    with _get_conn() as conn:
        cursor = conn.execute(
            "UPDATE users SET is_disabled = ? WHERE id = ?",
            (1 if disabled else 0, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def list_users() -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, username, email, is_admin, is_disabled, created_at, last_login
            FROM users
            ORDER BY created_at DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]
