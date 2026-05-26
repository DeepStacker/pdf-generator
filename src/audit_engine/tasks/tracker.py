"""Injectable thread-safe progress tracker — no module-level state."""

import logging
import threading
from datetime import datetime

from audit_engine.domain.models import ProgressInfo

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Tracks progress of a background generation task.

    Thread-safe: worker threads call update_pct/log, HTTP threads call snapshot.
    Each generation gets its own tracker instance.
    """

    def __init__(self) -> None:
        self._info = ProgressInfo()
        self._lock = threading.Lock()

    @property
    def pct(self) -> float:
        with self._lock:
            return self._info.pct

    @property
    def active_branch(self) -> str:
        with self._lock:
            return self._info.active_branch

    @property
    def logs(self) -> list[dict]:
        with self._lock:
            return list(self._info.logs)

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._info.is_running

    @is_running.setter
    def is_running(self, value: bool) -> None:
        with self._lock:
            self._info.is_running = value

    @property
    def summary(self) -> dict | None:
        with self._lock:
            return self._info.summary

    @summary.setter
    def summary(self, value: dict | None) -> None:
        with self._lock:
            self._info.summary = value

    @property
    def cancel_requested(self) -> bool:
        with self._lock:
            return self._info.cancel_requested

    @cancel_requested.setter
    def cancel_requested(self, value: bool) -> None:
        with self._lock:
            self._info.cancel_requested = value

    def log(self, level: str, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        with self._lock:
            self._info.logs.append({
                "timestamp": timestamp,
                "level": level,
                "message": str(message),
            })
        logger.info("[%s] %s", level, message)

    def update_pct(self, pct: float, active_branch: str = "") -> None:
        with self._lock:
            self._info.pct = pct
            if active_branch:
                self._info.active_branch = active_branch

    def reset(self) -> None:
        with self._lock:
            self._info = ProgressInfo()
            self._info.is_running = True

    def snapshot(self) -> dict:
        """Return current state as a plain dict (JSON-serializable)."""
        with self._lock:
            return {
                "pct": self._info.pct,
                "active_branch": self._info.active_branch,
                "logs": list(self._info.logs),
                "is_running": self._info.is_running,
                "summary": self._info.summary,
            }

    def __repr__(self) -> str:
        with self._lock:
            return f"ProgressTracker(pct={self._info.pct:.1f}, running={self._info.is_running})"
