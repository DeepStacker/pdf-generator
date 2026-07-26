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
                          audit_type TEXT,
                          full_path TEXT,
                          total_pay REAL DEFAULT 0,
                          pt_rows INTEGER DEFAULT 0,
                          md_rows INTEGER DEFAULT 0,
                          execution_time_sec REAL DEFAULT 0.1)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS consolidation_history
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          timestamp TEXT,
                          file_count INTEGER,
                          total_pay REAL DEFAULT 0,
                          pt_rows INTEGER DEFAULT 0,
                          md_rows INTEGER DEFAULT 0,
                          output_path TEXT,
                          status TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS config
                         (key TEXT PRIMARY KEY, value TEXT)''')
        with contextlib.suppress(sqlite3.OperationalError):
            cursor.execute("ALTER TABLE history ADD COLUMN full_path TEXT")
        with contextlib.suppress(sqlite3.OperationalError):
            cursor.execute("ALTER TABLE history ADD COLUMN total_pay REAL DEFAULT 0")
        with contextlib.suppress(sqlite3.OperationalError):
            cursor.execute("ALTER TABLE history ADD COLUMN pt_rows INTEGER DEFAULT 0")
        with contextlib.suppress(sqlite3.OperationalError):
            cursor.execute("ALTER TABLE history ADD COLUMN md_rows INTEGER DEFAULT 0")
        with contextlib.suppress(sqlite3.OperationalError):
            cursor.execute("ALTER TABLE history ADD COLUMN execution_time_sec REAL DEFAULT 0.1")
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


def log_generation(
    excel_name: str,
    pdf_count: int,
    output_path: str,
    audit_type: str,
    full_path: str | None = None,
    total_pay: float = 0.0,
    pt_rows: int = 0,
    md_rows: int = 0,
    execution_time_sec: float = 0.1,
) -> None:
    with _lock:
        conn = _get_connection()
        cursor = conn.cursor()
        safe_excel = os.path.basename(excel_name) if excel_name else "Audit Workbook"
        safe_full = full_path if full_path is not None else safe_excel
        safe_out = os.path.basename(output_path) if output_path else "Outputs"
        cursor.execute(
            "INSERT INTO history (timestamp, excel_name, pdf_count, output_path, audit_type, full_path, total_pay, pt_rows, md_rows, execution_time_sec) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), safe_excel, pdf_count, safe_out, audit_type, safe_full, total_pay, pt_rows, md_rows, execution_time_sec)
        )
        conn.commit()


def log_consolidation(file_count: int, total_pay: float, pt_rows: int, md_rows: int, output_path: str) -> None:
    with _lock:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO consolidation_history (timestamp, file_count, total_pay, pt_rows, md_rows, output_path, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), file_count, total_pay, pt_rows, md_rows, os.path.basename(output_path), "SUCCESS")
        )
        conn.commit()


def get_stats() -> tuple[int, int]:
    with _lock:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), COALESCE(SUM(pdf_count), 0) FROM history")
        res = cursor.fetchone()
        return (res[0] or 0, res[1] or 0)


def get_comprehensive_stats() -> dict[str, Any]:
    with _lock:
        conn = _get_connection()
        cursor = conn.cursor()

        # Audit stats
        cursor.execute("SELECT COUNT(*), COALESCE(SUM(pdf_count), 0), COALESCE(AVG(execution_time_sec), 0.1) FROM history")
        h_row = cursor.fetchone()
        h_runs = h_row[0] if h_row else 0
        h_pdfs = h_row[1] if h_row else 0
        h_avg_speed = h_row[2] if h_row else 0.1

        # Consolidation stats
        cursor.execute("SELECT COUNT(*), COALESCE(SUM(total_pay), 0), COALESCE(SUM(pt_rows), 0), COALESCE(SUM(md_rows), 0) FROM consolidation_history")
        c_row = cursor.fetchone()
        c_runs = c_row[0] if c_row else 0
        c_pay = c_row[1] if c_row else 0.0
        c_pt = c_row[2] if c_row else 0
        c_md = c_row[3] if c_row else 0

        # Audit type breakdown
        cursor.execute("SELECT audit_type, COUNT(*), COALESCE(SUM(pdf_count), 0), COALESCE(SUM(total_pay), 0) FROM history GROUP BY audit_type")
        audit_breakdown = [
            {"type": row[0] or "General", "runs": row[1], "pdfs": row[2], "pay": row[3]}
            for row in cursor.fetchall()
        ]

        # Monthly trends (last 6 months)
        cursor.execute("SELECT strftime('%b', timestamp) as m, COUNT(*), COALESCE(SUM(pdf_count), 0), COALESCE(SUM(total_pay), 0) FROM history GROUP BY strftime('%m', timestamp) ORDER BY timestamp DESC LIMIT 6")
        monthly_trends = [
            {"month": row[0] or "Mar", "pdfs": max(1, row[2]), "pay": row[3]}
            for row in reversed(cursor.fetchall())
        ]

        return {
            "total_reports": h_pdfs,
            "successful_runs": h_runs + c_runs,
            "total_consolidated_pay": c_pay,
            "pt_rows": c_pt,
            "md_rows": c_md,
            "avg_speed_sec": round(h_avg_speed, 2),
            "audit_breakdown": audit_breakdown,
            "monthly_trends": monthly_trends,
        }


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
        cursor.execute("DELETE FROM consolidation_history")
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
