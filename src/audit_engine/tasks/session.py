"""Per-user job state.

The engine kept one ProgressTracker and one cancel Event at module level, so
the whole server had a single running job: a second person was told "a
generation thread is already active", and the two would have shared a
progress bar and a cancel button if they had not been.

ProgressTracker was already written for this -- its own docstring says "Each
generation gets its own tracker instance" -- so the fix is routing, not a
rewrite. Each signed-in user gets a tracker and a cancel event, and the
worker threads reach theirs through a thread-local.

That indirection is deliberate: workers.py refers to `global_tracker` in
forty-four places and `cancel_event` in nine. Threading an argument through
all of them would be a large, error-prone diff across the code that actually
generates customers' reports. A proxy that resolves per thread leaves those
call sites untouched and correct.

The desktop is one person at one keyboard and binds nothing, so it resolves
to the default pair and behaves exactly as before.
"""

from __future__ import annotations

import threading

from audit_engine.tasks.tracker import ProgressTracker

# What a thread uses when nothing has been bound to it: the desktop app, and
# any code path that predates per-user sessions.
_default_tracker = ProgressTracker()
_default_cancel = threading.Event()

_local = threading.local()

# One pair per user, handed out on demand and kept for the life of the process
# so an HTTP thread can look up a worker thread's progress.
_sessions: dict[str, tuple[ProgressTracker, threading.Event]] = {}
_sessions_lock = threading.Lock()


def session_for(user: str | None) -> tuple[ProgressTracker, threading.Event]:
    """The tracker and cancel event belonging to `user`."""
    if not user:
        return _default_tracker, _default_cancel
    with _sessions_lock:
        if user not in _sessions:
            _sessions[user] = (ProgressTracker(), threading.Event())
        return _sessions[user]


def bind(user: str | None) -> None:
    """Point this thread at `user`'s job state and settings.

    Called for each HTTP request once the session is known, and again inside
    the worker thread the request starts -- a thread-local does not follow a
    new thread, and the worker is the one that reads auto_open and writes
    progress.
    """
    tracker, cancel = session_for(user)
    _local.tracker = tracker
    _local.cancel = cancel
    _local.user = user


def unbind() -> None:
    _local.tracker = None
    _local.cancel = None
    _local.user = None


def current_user() -> str | None:
    """Whose request or job this thread is serving. None for the desktop."""
    return getattr(_local, "user", None)


def current_tracker() -> ProgressTracker:
    return getattr(_local, "tracker", None) or _default_tracker


def current_cancel() -> threading.Event:
    return getattr(_local, "cancel", None) or _default_cancel


def active_users() -> list[str]:
    """Who currently has a run in flight."""
    with _sessions_lock:
        return [u for u, (tracker, _c) in _sessions.items() if tracker.is_running]


class _TrackerProxy:
    """Forwards every attribute to whichever tracker this thread is bound to."""

    def __getattr__(self, name):
        return getattr(current_tracker(), name)

    def __setattr__(self, name, value):
        setattr(current_tracker(), name, value)


class _CancelProxy:
    """Same, for the cancel event."""

    def __getattr__(self, name):
        return getattr(current_cancel(), name)


def run_bound(user: str | None, target, args=()) -> threading.Thread:
    """Start `target` on a thread bound to `user`'s job state."""
    def _runner():
        bind(user)
        try:
            target(*args)
        finally:
            unbind()

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    return thread
