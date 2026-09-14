import sqlite3
import uuid
from contextlib import contextmanager

from config import DB_PATH


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT UNIQUE,
                username TEXT,
                title TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id TEXT PRIMARY KEY,
                chat_id INTEGER,
                message_id INTEGER,
                title TEXT,
                added_by INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pending_submissions (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                user_chat_id INTEGER,
                message_id INTEGER,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # چون هر اجرای GitHub Actions یک پردازش کاملاً تازه و بی‌حافظه است، وضعیت
        # «منتظر آپلود» کاربر و آخرین update_id باید در دیتابیس نگه داشته شوند
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_state (
                user_id INTEGER PRIMARY KEY,
                awaiting_upload INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS kv_state (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)


# ---------- channels ----------

def add_channel(chat_id: str, username: str, title: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO channels (chat_id, username, title) VALUES (?, ?, ?)",
            (str(chat_id), username, title),
        )


def remove_channel(chat_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM channels WHERE chat_id = ?", (str(chat_id),))


def get_channels():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM channels").fetchall()


# ---------- videos ----------

def add_video(chat_id: int, message_id: int, title: str, added_by: int) -> str:
    video_id = uuid.uuid4().hex[:10]
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO videos (id, chat_id, message_id, title, added_by) VALUES (?, ?, ?, ?, ?)",
            (video_id, chat_id, message_id, title, added_by),
        )
    return video_id


def get_video(video_id: str):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM videos WHERE id = ?", (video_id,)).fetchone()


# ---------- pending submissions ----------

def add_pending_submission(user_id: int, user_chat_id: int, message_id: int) -> str:
    sub_id = uuid.uuid4().hex[:10]
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO pending_submissions (id, user_id, user_chat_id, message_id) VALUES (?, ?, ?, ?)",
            (sub_id, user_id, user_chat_id, message_id),
        )
    return sub_id


def get_pending_submission(sub_id: str):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM pending_submissions WHERE id = ?", (sub_id,)).fetchone()


def set_submission_status(sub_id: str, status: str):
    with get_conn() as conn:
        conn.execute("UPDATE pending_submissions SET status = ? WHERE id = ?", (status, sub_id))


# ---------- per-user state ----------

def set_awaiting_upload(user_id: int, value: bool):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO user_state (user_id, awaiting_upload) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET awaiting_upload = excluded.awaiting_upload",
            (user_id, int(value)),
        )


def is_awaiting_upload(user_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT awaiting_upload FROM user_state WHERE user_id = ?", (user_id,)
        ).fetchone()
        return bool(row and row["awaiting_upload"])


# ---------- وضعیت کلی ربات (مثل آخرین update_id دریافت‌شده از تلگرام) ----------

def get_state(key: str, default=None):
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM kv_state WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default


def set_state(key: str, value: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO kv_state (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )
