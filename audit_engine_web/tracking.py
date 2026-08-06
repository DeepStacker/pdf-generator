import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional

DB_PATH = Path(__file__).resolve().parent.parent / "report_tracking.db"


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_received TEXT NOT NULL,
            sol_id INTEGER NOT NULL,
            branch TEXT NOT NULL,
            accounts INTEGER NOT NULL,
            assigned_to TEXT NOT NULL,
            entry_type TEXT NOT NULL,
            entry_status TEXT NOT NULL,
            validation_status TEXT NOT NULL,
            validation_by TEXT NOT NULL DEFAULT '',
            remarks TEXT NOT NULL DEFAULT '-',
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)
    conn.commit()
    conn.close()


def list_records():
    conn = get_db()
    rows = conn.execute("SELECT * FROM tracking ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_record(data: dict) -> dict:
    conn = get_db()
    cur = conn.execute("""
        INSERT INTO tracking (date_received, sol_id, branch, accounts, assigned_to, entry_type, entry_status, validation_status, validation_by, remarks)
        VALUES (:date_received, :sol_id, :branch, :accounts, :assigned_to, :entry_type, :entry_status, :validation_status, :validation_by, :remarks)
    """, {
        "date_received": data["date_received"],
        "sol_id": data["sol_id"],
        "branch": data["branch"],
        "accounts": int(data["accounts"]),
        "assigned_to": data["assigned_to"],
        "entry_type": data["entry_type"],
        "entry_status": data["entry_status"],
        "validation_status": data["validation_status"],
        "validation_by": data.get("validation_by", ""),
        "remarks": data.get("remarks", "-"),
    })
    row_id = cur.lastrowid
    conn.commit()
    row = conn.execute("SELECT * FROM tracking WHERE id = ?", (row_id,)).fetchone()
    conn.close()
    return dict(row)


def update_record(record_id: int, data: dict) -> Optional[dict]:
    conn = get_db()
    existing = conn.execute("SELECT * FROM tracking WHERE id = ?", (record_id,)).fetchone()
    if not existing:
        conn.close()
        return None
    fields = ["date_received", "sol_id", "branch", "accounts", "assigned_to", "entry_type", "entry_status", "validation_status", "validation_by", "remarks"]
    updates = {k: data.get(k, existing[k]) for k in fields}
    updates["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
        UPDATE tracking SET date_received=:date_received, sol_id=:sol_id, branch=:branch, accounts=:accounts,
        assigned_to=:assigned_to, entry_type=:entry_type, entry_status=:entry_status,
        validation_status=:validation_status, validation_by=:validation_by, remarks=:remarks,
        updated_at=:updated_at WHERE id=:id
    """, {**updates, "id": record_id})
    conn.commit()
    row = conn.execute("SELECT * FROM tracking WHERE id = ?", (record_id,)).fetchone()
    conn.close()
    return dict(row)


def delete_record(record_id: int) -> bool:
    conn = get_db()
    cur = conn.execute("DELETE FROM tracking WHERE id = ?", (record_id,))
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


init_db()
