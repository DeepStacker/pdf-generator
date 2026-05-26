"""Data access layer — repository pattern for SQLite operations.

Legacy procedural functions are re-exported from legacy.py for backward
compatibility. New code should use the repository classes in repos.py.
"""

from audit_engine.database.legacy import (
    add_recent_file,
    clear_history,
    clear_recent_files,
    get_analytics,
    get_config,
    get_last_run,
    get_recent_files,
    get_recent_history,
    get_stats,
    get_total_unique_excels,
    init_db,
    log_generation,
    set_config,
)

__all__ = [
    "init_db", "set_config", "get_config", "log_generation",
    "get_stats", "get_analytics", "get_recent_history",
    "clear_history", "clear_recent_files", "get_recent_files",
    "add_recent_file", "get_last_run", "get_total_unique_excels",
]
