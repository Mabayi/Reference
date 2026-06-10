"""Token 管理存储。"""
import json
import sqlite3
from datetime import datetime, timedelta

from config.settings import BASE_DIR, settings

_db_relative = settings.DATABASE_URL.replace("sqlite:///", "")
DB_PATH = BASE_DIR / _db_relative


def _mask_api_key(api_key: str) -> str:
    value = api_key.strip()
    if len(value) <= 14:
        return f"{value[:4]}****"
    return f"{value[:7]}****{value[-6:]}"


def _load_balance_infos(value: str | None) -> list[dict]:
    try:
        data = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _format_balance_infos(balance_infos: list[dict]) -> str:
    if not balance_infos:
        return "未同步"
    parts = []
    for item in balance_infos:
        currency = str(item.get("currency") or "").strip()
        total = str(item.get("total_balance") or "0").strip()
        parts.append(f"{total} {currency}".strip())
    return " / ".join(parts) if parts else "未同步"


def _get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_token_tables():
    with _get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS token_balance (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 0,
                total_purchased INTEGER DEFAULT 0,
                total_redeemed INTEGER DEFAULT 0,
                is_disabled INTEGER DEFAULT 0
            )
            """
        )
        balance_columns = {row["name"] for row in conn.execute("PRAGMA table_info(token_balance)").fetchall()}
        if "is_disabled" not in balance_columns:
            conn.execute("ALTER TABLE token_balance ADD COLUMN is_disabled INTEGER DEFAULT 0")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS token_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                amount INTEGER NOT NULL,
                description TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS token_packages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                tokens INTEGER NOT NULL,
                price REAL NOT NULL,
                description TEXT DEFAULT ''
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS deepseek_api_keys (
                user_id INTEGER PRIMARY KEY,
                api_key TEXT NOT NULL,
                key_mask TEXT NOT NULL,
                is_available INTEGER DEFAULT 0,
                balance_infos TEXT DEFAULT '[]',
                checked_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        existing = conn.execute("SELECT COUNT(*) AS c FROM token_packages").fetchone()
        if existing["c"] == 0:
            conn.executemany(
                "INSERT INTO token_packages (name, tokens, price, description) VALUES (?, ?, ?, ?)",
                [
                    ("体验包", 1000, 0, "用于演示基础功能"),
                    ("基础包", 10000, 9.9, "适合轻量体验"),
                    ("标准包", 50000, 39.9, "适合作为日常演示资源"),
                    ("专业包", 200000, 99.9, "适合高频测试与展示"),
                ],
            )
        conn.commit()


def save_deepseek_api_key(user_id: int, api_key: str, balance_payload: dict) -> dict:
    balance_infos = balance_payload.get("balance_infos") or []
    is_available = 1 if balance_payload.get("is_available") else 0
    key_mask = _mask_api_key(api_key)
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO deepseek_api_keys (
                user_id, api_key, key_mask, is_available, balance_infos, checked_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                api_key = excluded.api_key,
                key_mask = excluded.key_mask,
                is_available = excluded.is_available,
                balance_infos = excluded.balance_infos,
                checked_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, api_key.strip(), key_mask, is_available, json.dumps(balance_infos, ensure_ascii=False)),
        )
        conn.execute(
            "INSERT INTO token_logs (user_id, action, amount, description) VALUES (?, 'bind_api_key', 0, ?)",
            (user_id, f"绑定 DeepSeek API Key：{key_mask}"),
        )
        conn.commit()
    return get_deepseek_api_key(user_id) or {}


def update_deepseek_balance(user_id: int, balance_payload: dict) -> dict | None:
    balance_infos = balance_payload.get("balance_infos") or []
    is_available = 1 if balance_payload.get("is_available") else 0
    with _get_conn() as conn:
        cursor = conn.execute(
            """
            UPDATE deepseek_api_keys
            SET is_available = ?,
                balance_infos = ?,
                checked_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (is_available, json.dumps(balance_infos, ensure_ascii=False), user_id),
        )
        if cursor.rowcount:
            conn.execute(
                "INSERT INTO token_logs (user_id, action, amount, description) VALUES (?, 'sync_balance', 0, '同步 DeepSeek 真实余额')",
                (user_id,),
            )
        conn.commit()
    return get_deepseek_api_key(user_id)


def get_deepseek_api_key(user_id: int, include_secret: bool = False) -> dict | None:
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM deepseek_api_keys WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            return None
        data = dict(row)
        data["balance_infos"] = _load_balance_infos(data.get("balance_infos"))
        data["balance_text"] = _format_balance_infos(data["balance_infos"])
        data["is_bound"] = True
        data["is_available"] = int(data.get("is_available") or 0)
        if not include_secret:
            data.pop("api_key", None)
        return data


def delete_deepseek_api_key(user_id: int) -> bool:
    existing = get_deepseek_api_key(user_id)
    with _get_conn() as conn:
        cursor = conn.execute("DELETE FROM deepseek_api_keys WHERE user_id = ?", (user_id,))
        if cursor.rowcount:
            conn.execute(
                "INSERT INTO token_logs (user_id, action, amount, description) VALUES (?, 'remove_api_key', 0, ?)",
                (user_id, f"移除 DeepSeek API Key：{existing.get('key_mask') if existing else '-'}"),
            )
        conn.commit()
        return cursor.rowcount > 0


def get_balance(user_id: int) -> dict:
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM token_balance WHERE user_id = ?", (user_id,)).fetchone()
        if row:
            return dict(row)

        conn.execute(
            "INSERT INTO token_balance (user_id, balance, total_purchased, total_redeemed) VALUES (?, 0, 0, 0)",
            (user_id,),
        )
        conn.commit()
        return {"user_id": user_id, "balance": 0, "total_purchased": 0, "total_redeemed": 0, "is_disabled": 0}


def is_token_disabled(user_id: int) -> bool:
    balance = get_balance(user_id)
    return bool(int(balance.get("is_disabled") or 0))


def record_api_usage(user_id: int, amount: int, description: str = "") -> bool:
    if amount <= 0:
        return False
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO token_logs (user_id, action, amount, description) VALUES (?, 'consume', ?, ?)",
            (user_id, -int(amount), description or "DeepSeek API 真实用量"),
        )
        conn.commit()
        return True


def consume_tokens(user_id: int, amount: int, description: str = "") -> bool:
    with _get_conn() as conn:
        balance = get_balance(user_id)
        if int(balance.get("is_disabled") or 0):
            return False
        if balance["balance"] < amount:
            return False

        conn.execute("UPDATE token_balance SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
        conn.execute(
            "INSERT INTO token_logs (user_id, action, amount, description) VALUES (?, 'consume', ?, ?)",
            (user_id, -amount, description),
        )
        conn.commit()
        return True


def add_tokens(user_id: int, amount: int, action: str = "purchase", description: str = "") -> bool:
    with _get_conn() as conn:
        balance = get_balance(user_id)
        if int(balance.get("is_disabled") or 0) and action != "admin":
            return False
        field = "total_purchased" if action == "purchase" else "total_redeemed"
        conn.execute(
            f"UPDATE token_balance SET balance = balance + ?, {field} = {field} + ? WHERE user_id = ?",
            (amount, amount, user_id),
        )
        conn.execute(
            "INSERT INTO token_logs (user_id, action, amount, description) VALUES (?, ?, ?, ?)",
            (user_id, action, amount, description),
        )
        conn.commit()
        return True


def get_logs(user_id: int, days: int = 7) -> list:
    with _get_conn() as conn:
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        rows = conn.execute(
            "SELECT * FROM token_logs WHERE user_id = ? AND created_at >= ? ORDER BY created_at DESC",
            (user_id, since),
        ).fetchall()
        return [dict(row) for row in rows]


def list_all_balances() -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                u.id AS user_id,
                u.username,
                u.email,
                u.is_admin,
                u.created_at,
                u.last_login,
                COALESCE(tb.balance, 0) AS balance,
                COALESCE(tb.total_purchased, 0) AS total_purchased,
                COALESCE(tb.total_redeemed, 0) AS total_redeemed,
                COALESCE(tb.is_disabled, 0) AS is_disabled,
                dk.key_mask AS deepseek_key_mask,
                COALESCE(dk.is_available, 0) AS deepseek_is_available,
                dk.balance_infos AS deepseek_balance_infos,
                dk.checked_at AS deepseek_checked_at
            FROM users u
            LEFT JOIN token_balance tb ON tb.user_id = u.id
            LEFT JOIN deepseek_api_keys dk ON dk.user_id = u.id
            ORDER BY u.created_at DESC
            """
        ).fetchall()
        users: list[dict] = []
        for row in rows:
            item = dict(row)
            balance_infos = _load_balance_infos(item.pop("deepseek_balance_infos", "[]"))
            item["deepseek_balance_infos"] = balance_infos
            item["deepseek_balance_text"] = _format_balance_infos(balance_infos)
            item["deepseek_is_bound"] = bool(item.get("deepseek_key_mask"))
            item["deepseek_is_available"] = int(item.get("deepseek_is_available") or 0)
            users.append(item)
        return users


def get_all_logs(limit: int = 100) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                l.*,
                u.username,
                u.email
            FROM token_logs l
            LEFT JOIN users u ON u.id = l.user_id
            ORDER BY l.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def set_token_disabled(user_id: int, disabled: bool, admin_id: int | None = None) -> None:
    with _get_conn() as conn:
        get_balance(user_id)
        conn.execute("UPDATE token_balance SET is_disabled = ? WHERE user_id = ?", (1 if disabled else 0, user_id))
        action = "disable" if disabled else "enable"
        description = f"管理员{admin_id or ''}停用 API 使用" if disabled else f"管理员{admin_id or ''}恢复 API 使用"
        conn.execute(
            "INSERT INTO token_logs (user_id, action, amount, description) VALUES (?, ?, 0, ?)",
            (user_id, action, description),
        )
        conn.commit()


def get_today_consumption(user_id: int) -> int:
    with _get_conn() as conn:
        today = datetime.now().strftime("%Y-%m-%d")
        row = conn.execute(
            "SELECT COALESCE(SUM(ABS(amount)), 0) AS total FROM token_logs WHERE user_id = ? AND action = 'consume' AND DATE(created_at) = ?",
            (user_id, today),
        ).fetchone()
        return row["total"]


def get_week_consumption(user_id: int) -> int:
    with _get_conn() as conn:
        since = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        row = conn.execute(
            "SELECT COALESCE(SUM(ABS(amount)), 0) AS total FROM token_logs WHERE user_id = ? AND action = 'consume' AND DATE(created_at) >= ?",
            (user_id, since),
        ).fetchone()
        return row["total"]


def get_packages() -> list:
    with _get_conn() as conn:
        rows = conn.execute("SELECT * FROM token_packages ORDER BY price").fetchall()
        return [dict(row) for row in rows]


def redeem_key(user_id: int, key: str) -> dict:
    return {
        "success": False,
        "message": "本地虚拟兑换已关闭。请绑定真实 DeepSeek API Key 并通过官方平台充值。",
    }
