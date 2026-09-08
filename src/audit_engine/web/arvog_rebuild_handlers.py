"""Arvog master-sheet rebuild handlers for the desktop app — path-based, zero-socket.

Same shape as the Flatten PDF handlers: a native dialog picks the workbook, the
work happens on a background thread against a path on disk, and the UI polls for
progress. Nothing is uploaded, so there is no copy of the auditor's sheet to
clean up — the rebuilt master appears beside the original, which is left
untouched.
"""

import os
import threading

from audit_engine.utils.dialogs import ask_file_dialog
from audit_engine.utils.platform import open_path

# What a workbook can be called. Anything else is refused before a thread starts.
EXCEL_SUFFIXES = (".xlsx", ".xlsm", ".xls")


class _RebuildTracker:
    """State for the single in-flight rebuild.

    One job at a time, matching the other tabs. Each attribute is written by the
    worker thread as a whole value and read by the polling thread, so no lock is
    needed.
    """

    def __init__(self) -> None:
        self.is_running: bool = False
        self.pct: int = 0
        self.progress_text: str = "Ready. Select a filled audit sheet."
        self.summary: dict = {}
        self.error_msg: str = ""
        self.logs: list[dict] = []

    def reset(self) -> None:
        self.is_running = True
        self.pct = 0
        self.progress_text = "Starting…"
        self.summary = {}
        self.error_msg = ""
        self.logs = []

    def log(self, level: str, message: str) -> None:
        from datetime import datetime
        self.logs.append({
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "level": level,
            "message": str(message),
        })
        if len(self.logs) > 200:
            self.logs.pop(0)


rebuild_tracker = _RebuildTracker()


def handle_arvog_rebuild_browse() -> dict:
    """Native picker for the filled audit sheet."""
    path = ask_file_dialog()
    return {"success": True, "path": path or ""}


def worker_arvog_rebuild_thread(filepath: str) -> None:
    from audit_engine.services.arvog_rebuild import RebuildError, rebuild_wide_workbook

    try:
        rebuild_tracker.log("INFO", f"Reading {os.path.basename(filepath)}")

        def on_progress(pct, message=""):
            rebuild_tracker.pct = int(pct)
            if message:
                rebuild_tracker.progress_text = message

        result = rebuild_wide_workbook(filepath, on_progress=on_progress)

        rebuild_tracker.log(
            "OK",
            f"{result['loans']} loan(s), {result['ornaments']} ornament(s) "
            f"folded into {result['columns']} columns",
        )
        if not result["audit_columns_found"]:
            rebuild_tracker.log(
                "WARN",
                "No audit block found in this sheet - the rebuilt master has the "
                "columns but they are empty.",
            )
        if result["formulas_replaced_with_values"]:
            rebuild_tracker.log(
                "WARN",
                f"{result['formulas_replaced_with_values']} formula(s) referred to cells "
                "the fold could not place; their last computed values were written instead.",
            )
        rebuild_tracker.log("OK", f"Saved: {result['output_path']}")

        rebuild_tracker.summary = result
        rebuild_tracker.pct = 100
        rebuild_tracker.progress_text = "Rebuild complete."
        rebuild_tracker.is_running = False

        from audit_engine.utils.platform import trigger_notification
        trigger_notification("Arvog Rebuild", f"Rebuilt {os.path.basename(filepath)}")
    except FileNotFoundError as e:
        _fail(str(e))
    except RebuildError as e:
        _fail(str(e))
    except Exception as e:  # noqa: BLE001 - nothing may escape the worker
        _fail(f"Unexpected error: {e}")


def _fail(message: str) -> None:
    rebuild_tracker.error_msg = message
    rebuild_tracker.log("ERROR", message)
    rebuild_tracker.progress_text = "Rebuild failed."
    rebuild_tracker.pct = 100
    rebuild_tracker.is_running = False


def handle_arvog_rebuild_run(data: dict) -> dict:
    data = data or {}
    filepath = (data.get("filepath") or "").strip()

    if not filepath:
        return {"success": False, "error": "No audit sheet selected."}
    if not os.path.exists(filepath):
        return {"success": False, "error": f"File not found: {filepath}"}
    if not filepath.lower().endswith(EXCEL_SUFFIXES):
        return {"success": False, "error": "Only Excel workbooks can be rebuilt."}
    if rebuild_tracker.is_running:
        return {"success": False, "error": "A rebuild is already running."}

    rebuild_tracker.reset()
    threading.Thread(target=worker_arvog_rebuild_thread, args=(filepath,), daemon=True).start()
    return {"success": True, "message": "Rebuild started."}


def handle_arvog_rebuild_progress() -> dict:
    return {
        "success": True,
        "is_running": rebuild_tracker.is_running,
        "pct": rebuild_tracker.pct,
        "progress_text": rebuild_tracker.progress_text,
        "logs": list(rebuild_tracker.logs),
        "summary": rebuild_tracker.summary or None,
        "error": rebuild_tracker.error_msg or None,
    }


def handle_arvog_rebuild_open(data: dict) -> dict:
    """Reveal the rebuilt master in the OS file manager."""
    path = ((data or {}).get("path") or "").strip()
    if not path or not os.path.exists(path):
        return {"success": False, "error": "Rebuilt file not found."}
    open_path(path)
    return {"success": True}
