import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "database.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            first_name TEXT DEFAULT '',
            last_name TEXT DEFAULT '',
            birth_year TEXT DEFAULT '',
            birth_month TEXT DEFAULT '',
            hobbies TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()


def add_user(user_id: int):
    conn = get_conn()
    conn.execute(
        """INSERT OR IGNORE INTO users (user_id)
           VALUES (?)""",
        (user_id,),
    )
    conn.commit()
    conn.close()


def update_field(user_id: int, field: str, value: str):
    allowed = {"first_name", "last_name", "birth_year", "birth_month", "hobbies"}
    if field not in allowed:
        raise ValueError(f"Недопустимое поле: {field}")
    conn = get_conn()
    conn.execute(
        f"""UPDATE users SET {field} = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?""",
        (value, user_id),
    )
    conn.commit()
    conn.close()


def get_user(user_id: int) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_users() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM users ORDER BY created_at").fetchall()
    conn.close()
    return [dict(r) for r in rows]
