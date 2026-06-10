import sqlite3

from config.settings import BASE_DIR, settings

_db_relative = settings.DATABASE_URL.replace("sqlite:///", "")
DB_PATH = BASE_DIR / _db_relative


def _get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_support_tables() -> None:
    with _get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS support_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                message TEXT NOT NULL,
                faq_key TEXT DEFAULT '',
                category TEXT DEFAULT '其他',
                sentiment TEXT DEFAULT '中性',
                sentiment_score INTEGER DEFAULT 2,
                priority TEXT DEFAULT '普通',
                ai_summary TEXT DEFAULT '',
                faq_answer TEXT DEFAULT '',
                ai_reply TEXT DEFAULT '',
                feedback TEXT DEFAULT '',
                feedback_note TEXT DEFAULT '',
                feedback_at DATETIME,
                source TEXT DEFAULT 'manual',
                status TEXT DEFAULT 'open',
                admin_reply TEXT DEFAULT '',
                admin_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(support_tickets)").fetchall()}
        migrations = {
            "faq_answer": "ALTER TABLE support_tickets ADD COLUMN faq_answer TEXT DEFAULT ''",
            "ai_reply": "ALTER TABLE support_tickets ADD COLUMN ai_reply TEXT DEFAULT ''",
            "feedback": "ALTER TABLE support_tickets ADD COLUMN feedback TEXT DEFAULT ''",
            "feedback_note": "ALTER TABLE support_tickets ADD COLUMN feedback_note TEXT DEFAULT ''",
            "feedback_at": "ALTER TABLE support_tickets ADD COLUMN feedback_at DATETIME",
            "source": "ALTER TABLE support_tickets ADD COLUMN source TEXT DEFAULT 'manual'",
        }
        for column, sql in migrations.items():
            if column not in columns:
                conn.execute(sql)
        conn.commit()


def create_ticket(
    *,
    user_id: int,
    subject: str,
    message: str,
    faq_key: str = "",
    category: str = "其他",
    sentiment: str = "中性",
    sentiment_score: int = 2,
    priority: str = "普通",
    ai_summary: str = "",
    faq_answer: str = "",
    ai_reply: str = "",
    source: str = "manual",
) -> dict:
    with _get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO support_tickets (
                user_id, subject, message, faq_key, category, sentiment,
                sentiment_score, priority, ai_summary, faq_answer, ai_reply, source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                subject,
                message,
                faq_key,
                category,
                sentiment,
                sentiment_score,
                priority,
                ai_summary,
                faq_answer,
                ai_reply,
                source,
            ),
        )
        conn.commit()
        return get_ticket_by_id(cursor.lastrowid)


def get_ticket_by_id(ticket_id: int) -> dict | None:
    with _get_conn() as conn:
        row = conn.execute(
            """
            SELECT
                t.*,
                u.username,
                u.email,
                admin.username AS admin_username
            FROM support_tickets t
            LEFT JOIN users u ON u.id = t.user_id
            LEFT JOIN users admin ON admin.id = t.admin_id
            WHERE t.id = ?
            """,
            (ticket_id,),
        ).fetchone()
        return dict(row) if row else None


def list_user_tickets(user_id: int, limit: int = 30) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM support_tickets
            WHERE user_id = ?
            ORDER BY updated_at DESC, created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]


def list_all_tickets(status: str = "all", limit: int = 100) -> list[dict]:
    where = ""
    values: list[object] = []
    if status != "all":
        where = "WHERE t.status = ?"
        values.append(status)
    values.append(limit)

    with _get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT
                t.*,
                u.username,
                u.email,
                admin.username AS admin_username
            FROM support_tickets t
            LEFT JOIN users u ON u.id = t.user_id
            LEFT JOIN users admin ON admin.id = t.admin_id
            {where}
            ORDER BY
                CASE t.priority
                    WHEN '紧急' THEN 0
                    WHEN '较高' THEN 1
                    ELSE 2
                END,
                t.updated_at DESC,
                t.created_at DESC
            LIMIT ?
            """,
            values,
        ).fetchall()
        return [dict(row) for row in rows]


def update_ticket_reply(ticket_id: int, admin_id: int, reply: str, status: str = "resolved") -> bool:
    with _get_conn() as conn:
        cursor = conn.execute(
            """
            UPDATE support_tickets
            SET admin_reply = ?, admin_id = ?, status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (reply, admin_id, status, ticket_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def update_ticket_status(ticket_id: int, status: str, admin_id: int | None = None) -> bool:
    with _get_conn() as conn:
        cursor = conn.execute(
            """
            UPDATE support_tickets
            SET status = ?, admin_id = COALESCE(?, admin_id), updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, admin_id, ticket_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def update_ticket_feedback(ticket_id: int, user_id: int, helpful: bool, note: str = "") -> dict | None:
    feedback = "helpful" if helpful else "not_helpful"
    status = "resolved" if helpful else "open"
    with _get_conn() as conn:
        cursor = conn.execute(
            """
            UPDATE support_tickets
            SET feedback = ?,
                feedback_note = ?,
                feedback_at = CURRENT_TIMESTAMP,
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            """,
            (feedback, note, status, ticket_id, user_id),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return None
    return get_ticket_by_id(ticket_id)


def get_ticket_stats() -> dict:
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT status, COUNT(*) AS total
            FROM support_tickets
            GROUP BY status
            """
        ).fetchall()
        stats = {"open": 0, "in_progress": 0, "resolved": 0, "closed": 0}
        for row in rows:
            stats[row["status"]] = row["total"]
        stats["total"] = sum(stats.values())
        return stats


def get_feedback_stats() -> dict:
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT feedback, COUNT(*) AS total
            FROM support_tickets
            WHERE feedback != ''
            GROUP BY feedback
            """
        ).fetchall()
        stats = {"helpful": 0, "not_helpful": 0}
        for row in rows:
            if row["feedback"] in stats:
                stats[row["feedback"]] = row["total"]
        stats["total"] = sum(stats.values())
        return stats
