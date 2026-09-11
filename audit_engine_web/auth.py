"""Password gate for the browser server.

The desktop app does not import this and is unaffected: it speaks to the same
handlers over an in-process bridge and never opens a socket, so there is no
request for anyone else to make.

The browser server is the opposite case -- it is reachable from the public
internet, and every route behind it uploads, generates or hands back a
customer's audit reports. It previously authenticated nobody at all.

Design notes worth knowing before changing anything here:

* The password is never stored, only a PBKDF2-SHA256 hash of it, and it is
  read from the environment rather than a file in the repo.
* Comparisons are constant-time. A timing difference on a password check is
  small but free to avoid.
* It fails closed. With no password configured the server refuses every
  request rather than serving openly, because the failure mode of the
  alternative is silently publishing customer data.
* Sessions are signed cookies, so there is no server-side session store to
  keep, expire or leak. The signature covers the issue time, which is what
  makes expiry enforceable rather than advisory.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import secrets
import time

logger = logging.getLogger(__name__)

PASSWORD_ENV = "GSS_AUTH_PASSWORD_HASH"
SECRET_ENV = "GSS_SECRET_KEY"
USER_ENV = "GSS_AUTH_USER"

COOKIE_NAME = "gss_session"
SESSION_MAX_AGE = 12 * 60 * 60  # a working day; re-login the next morning

_PBKDF2_ROUNDS = 240_000


def hash_password(password: str, *, rounds: int = _PBKDF2_ROUNDS) -> str:
    """Produce the value GSS_AUTH_PASSWORD_HASH expects."""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, rounds)
    return f"pbkdf2_sha256${rounds}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt_b64, hash_b64 = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt_b64), int(rounds))
        return hmac.compare_digest(dk, base64.b64decode(hash_b64))
    except (ValueError, TypeError):
        return False


def expected_user() -> str:
    return os.environ.get(USER_ENV, "admin")


def is_configured() -> bool:
    return bool(os.environ.get(PASSWORD_ENV, "").strip())


def _secret() -> bytes:
    configured = os.environ.get(SECRET_ENV, "").strip()
    if configured:
        return configured.encode()
    # Without one, sessions simply do not survive a restart -- everyone is
    # asked to sign in again after a deploy. That is an annoyance, not a hole,
    # so it warns rather than refusing to start the way a missing password does.
    global _EPHEMERAL_SECRET
    if _EPHEMERAL_SECRET is None:
        _EPHEMERAL_SECRET = secrets.token_bytes(32)
        logger.warning(
            "%s is not set: signing sessions with a key generated at startup, "
            "so everyone is signed out whenever this process restarts.", SECRET_ENV
        )
    return _EPHEMERAL_SECRET


_EPHEMERAL_SECRET: bytes | None = None


def issue_session() -> str:
    """A signed `issued_at.signature` token. No server-side state to keep."""
    issued = str(int(time.time()))
    signature = hmac.new(_secret(), issued.encode(), hashlib.sha256).hexdigest()
    return f"{issued}.{signature}"


def session_is_valid(token: str | None) -> bool:
    if not token:
        return False
    try:
        issued, signature = token.rsplit(".", 1)
    except ValueError:
        return False

    expected = hmac.new(_secret(), issued.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return False

    try:
        age = time.time() - int(issued)
    except ValueError:
        return False
    return 0 <= age <= SESSION_MAX_AGE


# --- Login throttling -------------------------------------------------------
#
# The server is on the public internet, so an unthrottled password form is an
# open invitation to guess at line speed. Held in memory: this runs as a
# single process, and a restart clearing the counters costs an attacker more
# than it costs a user who mistyped.

_FAILURES: dict[str, list[float]] = {}
_WINDOW = 15 * 60
_MAX_ATTEMPTS = 8


def note_failure(client: str) -> None:
    now = time.time()
    recent = [t for t in _FAILURES.get(client, []) if now - t < _WINDOW]
    recent.append(now)
    _FAILURES[client] = recent


def clear_failures(client: str) -> None:
    _FAILURES.pop(client, None)


def is_throttled(client: str) -> bool:
    now = time.time()
    recent = [t for t in _FAILURES.get(client, []) if now - t < _WINDOW]
    _FAILURES[client] = recent
    return len(recent) >= _MAX_ATTEMPTS
