"""PDF Flatten handlers for the desktop app — path-based, zero-socket.

Same shape as the Report Validator's desktop handlers: a native dialog picks
the file, the work happens on a background thread against a path on disk, and
the UI polls for progress. Nothing is uploaded, so on the desktop there is no
copy of the user's PDF to clean up — the flattened file simply appears beside
the original, which is left untouched.
"""

import os
import threading

from audit_engine.utils.dialogs import ask_pdf_file_dialog
from audit_engine.utils.platform import open_path


class _FlattenTracker:
    """State for the single in-flight flatten job.

    One job at a time, matching the other tabs. Each attribute is written by
    the worker thread as a whole value and read by the polling thread, so no
    lock is needed.
    """

    def __init__(self) -> None:
        self.is_running: bool = False
        self.pct: int = 0
        self.progress_text: str = "Ready. Select a PDF to flatten."
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


flatten_tracker = _FlattenTracker()


def handle_flatten_browse() -> dict:
    """Native picker for the PDF to flatten."""
    path = ask_pdf_file_dialog()
    return {"success": True, "path": path or ""}


def worker_flatten_thread(filepath: str) -> None:
    from audit_engine.services.pdf_flattener import FlattenError, flatten_pdf

    try:
        flatten_tracker.log("INFO", f"Reading {os.path.basename(filepath)}")

        def on_progress(pct, message=""):
            flatten_tracker.pct = int(pct)
            if message:
                flatten_tracker.progress_text = message

        result = flatten_pdf(filepath, on_progress=on_progress)

        flatten_tracker.log(
            "OK",
            f"{result['pages']} page(s), {result['fields_flattened']} field(s) baked in, "
            f"{result['links_removed']} link(s) removed",
        )
        flatten_tracker.log("OK", f"Saved: {result['output_path']}")

        flatten_tracker.summary = result
        flatten_tracker.pct = 100
        flatten_tracker.progress_text = "Flatten complete."
        flatten_tracker.is_running = False

        from audit_engine.utils.platform import trigger_notification
        trigger_notification("PDF Flatten", f"Flattened {os.path.basename(filepath)}")
    except FileNotFoundError as e:
        _fail(str(e))
    except FlattenError as e:
        _fail(str(e))
    except Exception as e:  # noqa: BLE001 - nothing may escape the worker
        _fail(f"Unexpected error: {e}")


def _fail(message: str) -> None:
    flatten_tracker.error_msg = message
    flatten_tracker.log("ERROR", message)
    flatten_tracker.progress_text = "Flatten failed."
    flatten_tracker.pct = 100
    flatten_tracker.is_running = False


def handle_flatten_run(data: dict) -> dict:
    data = data or {}
    filepath = (data.get("filepath") or "").strip()

    if not filepath:
        return {"success": False, "error": "No PDF selected."}
    if not os.path.exists(filepath):
        return {"success": False, "error": f"File not found: {filepath}"}
    if not filepath.lower().endswith(".pdf"):
        return {"success": False, "error": "Only .pdf files can be flattened."}
    if flatten_tracker.is_running:
        return {"success": False, "error": "A flatten is already running."}

    flatten_tracker.reset()
    threading.Thread(target=worker_flatten_thread, args=(filepath,), daemon=True).start()
    return {"success": True, "message": "Flatten started."}


def handle_flatten_progress() -> dict:
    return {
        "success": True,
        "is_running": flatten_tracker.is_running,
        "pct": flatten_tracker.pct,
        "progress_text": flatten_tracker.progress_text,
        "logs": list(flatten_tracker.logs),
        "summary": flatten_tracker.summary or None,
        "error": flatten_tracker.error_msg or None,
    }


def handle_flatten_open(data: dict) -> dict:
    """Reveal the flattened PDF in the OS file manager."""
    path = ((data or {}).get("path") or "").strip()
    if not path or not os.path.exists(path):
        return {"success": False, "error": "Flattened file not found."}
    open_path(path)
    return {"success": True}
