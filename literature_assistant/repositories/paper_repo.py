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


def _column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row["name"] == column_name for row in rows)


def init_papers_table():
    """创建 papers 表和文献文件夹表，并补齐旧库缺少的列。"""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS paper_folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                parent_id INTEGER,
                name TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                stored_name TEXT NOT NULL,
                title TEXT,
                authors TEXT,
                abstract TEXT,
                keywords TEXT,
                year INTEGER,
                methods TEXT,
                conclusions TEXT,
                innovations TEXT,
                parse_status TEXT DEFAULT 'pending',
                file_md5 TEXT,
                folder_id INTEGER,
                paper_tier TEXT DEFAULT 'A',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        if not _column_exists(conn, "papers", "folder_id"):
            conn.execute("ALTER TABLE papers ADD COLUMN folder_id INTEGER")
        if not _column_exists(conn, "papers", "paper_tier"):
            conn.execute("ALTER TABLE papers ADD COLUMN paper_tier TEXT DEFAULT 'A'")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_user_folder ON papers(user_id, folder_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_user_tier ON papers(user_id, paper_tier)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_folders_user_parent ON paper_folders(user_id, parent_id)")
        conn.commit()


def get_folder_by_id(folder_id: int, user_id: int) -> dict | None:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM paper_folders WHERE id = ? AND user_id = ?",
            (folder_id, user_id),
        ).fetchone()
        return dict(row) if row else None


def _find_folder(conn: sqlite3.Connection, user_id: int, name: str, parent_id: int | None) -> sqlite3.Row | None:
    if parent_id is None:
        return conn.execute(
            """
            SELECT * FROM paper_folders
            WHERE user_id = ? AND parent_id IS NULL AND lower(name) = lower(?)
            """,
            (user_id, name),
        ).fetchone()
    return conn.execute(
        """
        SELECT * FROM paper_folders
        WHERE user_id = ? AND parent_id = ? AND lower(name) = lower(?)
        """,
        (user_id, parent_id, name),
    ).fetchone()


def create_folder(user_id: int, name: str, parent_id: int | None = None) -> dict:
    with _get_conn() as conn:
        if parent_id is not None:
            parent = conn.execute(
                "SELECT id FROM paper_folders WHERE id = ? AND user_id = ?",
                (parent_id, user_id),
            ).fetchone()
            if not parent:
                raise ValueError("父文件夹不存在")

        existing = _find_folder(conn, user_id, name, parent_id)
        if existing:
            raise ValueError("同级目录下已存在同名文件夹")

        cursor = conn.execute(
            "INSERT INTO paper_folders (user_id, parent_id, name) VALUES (?, ?, ?)",
            (user_id, parent_id, name),
        )
        conn.commit()
        return get_folder_by_id(cursor.lastrowid, user_id)


def get_or_create_folder(user_id: int, name: str, parent_id: int | None = None) -> int:
    with _get_conn() as conn:
        existing = _find_folder(conn, user_id, name, parent_id)
        if existing:
            return int(existing["id"])
        cursor = conn.execute(
            "INSERT INTO paper_folders (user_id, parent_id, name) VALUES (?, ?, ?)",
            (user_id, parent_id, name),
        )
        conn.commit()
        return int(cursor.lastrowid)


def get_folders_by_user(user_id: int) -> list:
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                f.*,
                COUNT(p.id) AS paper_count
            FROM paper_folders f
            LEFT JOIN papers p ON p.folder_id = f.id AND p.user_id = f.user_id
            WHERE f.user_id = ?
            GROUP BY f.id
            ORDER BY f.parent_id IS NOT NULL, f.name COLLATE NOCASE
            """,
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def create_paper(
    user_id: int,
    filename: str,
    stored_name: str,
    file_md5: str,
    folder_id: int | None = None,
) -> int:
    with _get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO papers (user_id, filename, stored_name, file_md5, folder_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, filename, stored_name, file_md5, folder_id),
        )
        conn.commit()
        return cursor.lastrowid


def update_paper_metadata(paper_id: int, **kwargs):
    """更新文献元数据字段。"""
    allowed = {
        "title",
        "authors",
        "abstract",
        "keywords",
        "year",
        "methods",
        "conclusions",
        "innovations",
        "parse_status",
        "folder_id",
        "paper_tier",
    }
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    for key in ("authors", "keywords"):
        if key in fields and isinstance(fields[key], list):
            fields[key] = json.dumps(fields[key], ensure_ascii=False)
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [paper_id]
    with _get_conn() as conn:
        conn.execute(f"UPDATE papers SET {set_clause} WHERE id = ?", values)
        conn.commit()


def get_papers_by_user(
    user_id: int,
    *,
    scope: str = "all",
    folder_id: int | None = None,
    query: str = "",
) -> list:
    where = ["p.user_id = ?"]
    values: list[object] = [user_id]

    if scope == "root":
        where.append("p.folder_id IS NULL")
    elif scope == "folder":
        where.append("p.folder_id = ?")
        values.append(folder_id)

    query = query.strip()
    if query:
        like = f"%{query}%"
        where.append(
            """
            (
                p.filename LIKE ?
                OR p.title LIKE ?
                OR p.authors LIKE ?
                OR p.keywords LIKE ?
                OR f.name LIKE ?
                OR p.paper_tier LIKE ?
            )
            """
        )
        values.extend([like, like, like, like, like, like])

    sql = f"""
        SELECT p.*, f.name AS folder_name
        FROM papers p
        LEFT JOIN paper_folders f ON f.id = p.folder_id AND f.user_id = p.user_id
        WHERE {' AND '.join(where)}
        ORDER BY p.created_at DESC
    """
    with _get_conn() as conn:
        rows = conn.execute(sql, values).fetchall()
        return [dict(r) for r in rows]


def get_paper_by_id(paper_id: int, user_id: int) -> dict | None:
    with _get_conn() as conn:
        row = conn.execute(
            """
            SELECT p.*, f.name AS folder_name
            FROM papers p
            LEFT JOIN paper_folders f ON f.id = p.folder_id AND f.user_id = p.user_id
            WHERE p.id = ? AND p.user_id = ?
            """,
            (paper_id, user_id),
        ).fetchone()
        return dict(row) if row else None


def update_paper_record(
    paper_id: int,
    user_id: int,
    *,
    filename: str | None = None,
    paper_tier: str | None = None,
    folder_id: int | None = None,
    update_folder: bool = False,
) -> bool:
    fields: dict[str, object] = {}
    if filename is not None:
        fields["filename"] = filename
    if paper_tier is not None:
        fields["paper_tier"] = paper_tier
    if update_folder:
        fields["folder_id"] = folder_id
    if not fields:
        return False

    set_clause = ", ".join(f"{key} = ?" for key in fields)
    values = list(fields.values()) + [paper_id, user_id]
    with _get_conn() as conn:
        cursor = conn.execute(
            f"UPDATE papers SET {set_clause} WHERE id = ? AND user_id = ?",
            values,
        )
        conn.commit()
        return cursor.rowcount > 0


def rename_paper(paper_id: int, user_id: int, filename: str) -> bool:
    return update_paper_record(paper_id, user_id, filename=filename)


def delete_paper(paper_id: int, user_id: int) -> bool:
    with _get_conn() as conn:
        cursor = conn.execute(
            "DELETE FROM papers WHERE id = ? AND user_id = ?",
            (paper_id, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def check_md5_exists(user_id: int, file_md5: str) -> bool:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM papers WHERE user_id = ? AND file_md5 = ?",
            (user_id, file_md5),
        ).fetchone()
        return row is not None
