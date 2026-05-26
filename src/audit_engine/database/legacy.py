"""SQLite database operations with lazy singleton connection.

Connection is opened on first use and reused for the lifetime of the process.
Safer than open/close per call — reduces file-system churn and connection
overhead, and is still safe for single-process use with check_same_thread=False.
"""

import contextlib
import os
import sqlite3
import threading
from datetime import datetime
from typing import Any

from audit_engine.utils.config import paths, ui

_lock = threading.Lock()


class _Connection:
    _instance: sqlite3.Connection | None = None
    _lock = threading.Lock()

    @classmethod
    def get(cls) -> sqlite3.Connection:
        with cls._lock:
            if cls._instance is None:
                cls._instance = sqlite3.connect(paths.db, check_same_thread=False)
                cls._instance.row_factory = sqlite3.Row
            return cls._instance


def _get_connection() -> sqlite3.Connection:
    return _Connection.get()


def init_db() -> None:
    with _lock:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS history
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          timestamp TEXT,
                          excel_name TEXT,
                          pdf_count INTEGER,
                          output_path TEXT,
                          audit_type TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS config
                         (key TEXT PRIMARY KEY, value TEXT)''')
        with contextlib.suppress(sqlite3.OperationalError):
            cursor.execute("ALTER TABLE history ADD COLUMN full_path TEXT")
        conn.commit()


def set_config(key: str, value: Any) -> None:
    with _lock:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()


def get_config(key: str, default: str | None = None) -> str | None:
    with _lock:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
        res = cursor.fetchone()
        return res[0] if res else default


def log_generation(excel_name: str, pdf_count: int, output_path: str, audit_type: str, full_path: str | None = None) -> None:
    with _lock:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO history (timestamp, excel_name, pdf_count, output_path, audit_type, full_path) VALUES (?, ?, ?, ?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), excel_name, pdf_count, output_path, audit_type, full_path)
        )
        conn.commit()


def get_stats() -> tuple[int, int]:
    with _lock:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), SUM(pdf_count) FROM history")
        res = cursor.fetchone()
        return (res[0] or 0, res[1] or 0)


def get_analytics() -> tuple[dict[str, int], list[tuple[str, int]]]:
    with _lock:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT audit_type, COUNT(*) FROM history GROUP BY audit_type")
        types: dict[str, int] = dict(cursor.fetchall())
        cursor.execute("SELECT strftime('%Y-%m-%d', timestamp), COUNT(*) FROM history GROUP BY 1 ORDER BY 1 DESC LIMIT 7")
        trend: list[tuple[str, int]] = cursor.fetchall()
        return types, trend


def get_recent_history(search: str = "", limit: int = 100) -> list[tuple]:
    with _lock:
        conn = _get_connection()
        cursor = conn.cursor()
        if search:
            cursor.execute(
                "SELECT id, timestamp, excel_name, pdf_count, output_path, audit_type, full_path FROM history WHERE excel_name LIKE ? ORDER BY id DESC LIMIT ?",
                (f"%{search}%", limit)
            )
        else:
            cursor.execute(
                "SELECT id, timestamp, excel_name, pdf_count, output_path, audit_type, full_path FROM history ORDER BY id DESC LIMIT ?",
                (limit,)
            )
        return cursor.fetchall()


def clear_history() -> None:
    with _lock:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM history")
        conn.commit()


def clear_recent_files() -> None:
    with _lock:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM config WHERE key LIKE 'recent_file_%'")
        conn.commit()


def get_recent_files() -> list[str]:
    with _lock:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM config WHERE key LIKE 'recent_file_%' ORDER BY key")
        files: list[str] = []
        for row in cursor.fetchall():
            f = row[0]
            if f and os.path.exists(f) and f not in files:
                files.append(f)
        return files


def add_recent_file(filepath: str) -> None:
    with _lock:
        conn = _get_connection()
        cursor = conn.cursor()
        filepath = os.path.abspath(os.path.normpath(filepath))

        cursor.execute("SELECT value FROM config WHERE key LIKE 'recent_file_%' ORDER BY key")
        existing = [row[0] for row in cursor.fetchall() if row[0] and row[0] != filepath and os.path.exists(row[0])]

        existing.insert(0, filepath)
        existing = existing[:ui.max_recent_files]

        cursor.execute("DELETE FROM config WHERE key LIKE 'recent_file_%'")
        for i, f in enumerate(existing):
            cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (f"recent_file_{i}", f))
        conn.commit()


def get_last_run() -> str:
    with _lock:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp FROM history ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else "No activity yet"


def get_total_unique_excels() -> int:
    with _lock:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT excel_name) FROM history")
        return cursor.fetchone()[0] or 0
