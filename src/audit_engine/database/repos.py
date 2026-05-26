"""Repository classes for config and history persistence.

Wraps the legacy procedural database module with proper OOP repositories.
Eliminates import-time side effects and provides a testable surface.
"""

import builtins

from audit_engine import database as _db
from audit_engine.domain.models import HistoryEntry

_FULL_PATH_IDX = 6


class ConfigRepository:
    """Key-value configuration store with in-memory cache."""

    _NOT_FOUND = object()

    def __init__(self) -> None:
        self._cache: dict[str, str | object] = {}

    def _clear_cache(self) -> None:
        self._cache.clear()

    def get(self, key: str, default: str | None = None) -> str | None:
        if key not in self._cache:
            val = _db.get_config(key)
            self._cache[key] = val if val is not None else self._NOT_FOUND
        val = self._cache[key]
        return val if val is not self._NOT_FOUND else default

    def set(self, key: str, value: str) -> None:
        self._cache[key] = value
        _db.set_config(key, value)

    def get_bool(self, key: str, default: bool = True) -> bool:
        val = self.get(key, str(default))
        return val == "True" if val is not None else default

    def get_int(self, key: str, default: int = 0) -> int:
        val = self.get(key)
        return int(val) if val is not None and val.isdigit() else default

    def clear_recent_files(self) -> None:
        _db.clear_recent_files()

    def get_recent_files(self) -> list[str]:
        return _db.get_recent_files()

    def add_recent_file(self, filepath: str) -> None:
        _db.add_recent_file(filepath)


class HistoryRepository:
    """Generation history store."""

    def add(self, excel_name: str, pdf_count: int, output_path: str, audit_type: str, full_path: str | None = None) -> None:
        _db.log_generation(excel_name, pdf_count, output_path, audit_type, full_path)

    def list(self, search: str = "", limit: int = 100) -> builtins.list[HistoryEntry]:
        rows = _db.get_recent_history(search, limit)
        return [
            HistoryEntry(
                id=r[0], timestamp=r[1], excel_name=r[2],
                pdf_count=r[3], output_path=r[4], audit_type=r[5],
                full_path=r[_FULL_PATH_IDX] if len(r) > _FULL_PATH_IDX else "",
            )
            for r in rows
        ]

    def clear(self) -> None:
        _db.clear_history()

    def stats(self) -> tuple[int, int]:
        return _db.get_stats()

    def analytics(self) -> tuple[dict[str, int], builtins.list[tuple[str, int]]]:
        return _db.get_analytics()

    def last_run(self) -> str:
        return _db.get_last_run()

    def total_unique_excels(self) -> int:
        return _db.get_total_unique_excels()


# Singleton repositories for the standard application flow.
# Tests can instantiate fresh copies when needed.
config_repo = ConfigRepository()
history_repo = HistoryRepository()
