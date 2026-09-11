"""Accounts for the browser app.

One password in an environment variable was right while one person used
this. It cannot express "these five people, each with their own settings and
their own work", and rotating it signs everybody out at once.

Accounts live in the same SQLite database as everything else, so they ride
the existing volume and backups. The password itself is never stored -- only
the PBKDF2 hash, in the "$"-free encoding that survives a compose env file
(see auth.py for why that matters).

Bootstrapping is automatic: on first use, an existing GSS_AUTH_PASSWORD_HASH
is adopted as the admin account, so upgrading does not lock anyone out and
nothing has to be re-entered by hand.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime

from audit_engine.utils.config import paths
from audit_engine_web import auth

_USERNAME_MAX = 40


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(paths.db, check_same_thread=False)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS users (
               username      TEXT PRIMARY KEY,
               password_hash TEXT NOT NULL,
               is_admin      INTEGER NOT NULL DEFAULT 0,
               created_at    TEXT NOT NULL
           )"""
    )
    conn.commit()
    return conn


def normalise(username: str) -> str:
    return (username or "").strip().lower()


def is_valid_username(username: str) -> bool:
    """Usernames key a directory on disk, so keep them boring."""
    name = normalise(username)
    return (
        bool(name)
        and len(name) <= _USERNAME_MAX
        and all(c.isalnum() or c in "._-" for c in name)
        and not name.startswith(".")
    )


def ensure_bootstrapped() -> None:
    """Adopt the single env-var login as the first admin, once."""
    conn = _connect()
    try:
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
            return
        env_hash = os.environ.get(auth.PASSWORD_ENV, "").strip()
        if not env_hash:
            return
        conn.execute(
            "INSERT INTO users (username, password_hash, is_admin, created_at) VALUES (?, ?, 1, ?)",
            (normalise(os.environ.get(auth.USER_ENV, "admin")), env_hash, datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
    finally:
        conn.close()


def list_users() -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT username, is_admin, created_at FROM users ORDER BY username"
        ).fetchall()
    finally:
        conn.close()
    return [{"username": r[0], "is_admin": bool(r[1]), "created_at": r[2]} for r in rows]


def count_admins() -> int:
    conn = _connect()
    try:
        return conn.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1").fetchone()[0]
    finally:
        conn.close()


def get_user(username: str) -> dict | None:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT username, password_hash, is_admin FROM users WHERE username = ?",
            (normalise(username),),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    return {"username": row[0], "password_hash": row[1], "is_admin": bool(row[2])}


def verify(username: str, password: str) -> dict | None:
    """The account if the password is right, otherwise None."""
    user = get_user(username)
    if not user:
        # Hash anyway: returning instantly for an unknown name tells an
        # attacker which names exist.
        auth.verify_password(password, auth.hash_password("decoy"))
        return None
    if auth.verify_password(password, user["password_hash"]):
        return user
    return None


def add_user(username: str, password: str, *, is_admin: bool = False) -> tuple[bool, str]:
    name = normalise(username)
    if not is_valid_username(name):
        return False, "Use letters, digits, dot, dash or underscore (max 40)."
    if len(password) < 12:
        return False, "Use at least 12 characters: this server faces the internet."
    if get_user(name):
        return False, f"{name} already exists."
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, is_admin, created_at) VALUES (?, ?, ?, ?)",
            (name, auth.hash_password(password), 1 if is_admin else 0,
             datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
    finally:
        conn.close()
    return True, f"Added {name}."


def set_password(username: str, password: str) -> tuple[bool, str]:
    name = normalise(username)
    if len(password) < 12:
        return False, "Use at least 12 characters."
    if not get_user(name):
        return False, f"{name} does not exist."
    conn = _connect()
    try:
        conn.execute("UPDATE users SET password_hash = ? WHERE username = ?",
                     (auth.hash_password(password), name))
        conn.commit()
    finally:
        conn.close()
    return True, f"Password updated for {name}."


def set_admin(username: str, is_admin: bool) -> tuple[bool, str]:
    name = normalise(username)
    if not get_user(name):
        return False, f"{name} does not exist."
    # Removing the last admin would leave the server with no one able to manage
    # accounts, and no way back except the host.
    if not is_admin and count_admins() <= 1 and get_user(name)["is_admin"]:
        return False, "That is the only admin left."
    conn = _connect()
    try:
        conn.execute("UPDATE users SET is_admin = ? WHERE username = ?", (1 if is_admin else 0, name))
        conn.commit()
    finally:
        conn.close()
    return True, f"{name} is {'now an admin' if is_admin else 'no longer an admin'}."


def delete_user(username: str) -> tuple[bool, str]:
    name = normalise(username)
    user = get_user(name)
    if not user:
        return False, f"{name} does not exist."
    if user["is_admin"] and count_admins() <= 1:
        return False, "That is the only admin left."
    conn = _connect()
    try:
        conn.execute("DELETE FROM users WHERE username = ?", (name,))
        conn.commit()
    finally:
        conn.close()
    return True, f"Removed {name}."
