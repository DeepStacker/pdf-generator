"""Merge PDF handlers for the desktop app — path-based, zero-socket.

The desktop picks the root folder with a native dialog and merges it in
place on disk, so nothing is uploaded and there is no temporary copy to
shred afterwards. The zip is written beside the folder that was picked,
never inside it: a zip dropped into the root would sit alongside the branch
folders the next run scans, and the run's own output would start looking
like input.
"""

import os
import threading
from pathlib import Path

from audit_engine.utils.dialogs import ask_directory_dialog
from audit_engine.utils.platform import open_path


class _MergeTracker:
    """State for the single in-flight merge job.

    One job at a time, matching the other tools. Each attribute is written
    by the worker thread as a whole value and read by the polling thread,
    so no lock is needed.
    """

    def __init__(self) -> None:
        self.is_running: bool = False
        self.pct: int = 0
        self.progress_text: str = "Ready. Select a folder of branch folders."
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


merge_tracker = _MergeTracker()


def handle_merge_browse() -> dict:
    """Native picker for the root folder holding the branch folders."""
    path = ask_directory_dialog()
    return {"success": True, "path": path or ""}


def _zip_destination(root: Path) -> Path:
    """Where this run's zip goes: beside the picked folder, never over an
    earlier run's output."""
    parent = root.parent if os.access(root.parent, os.W_OK) else root
    base = f"{root.name}_Merged"
    candidate = parent / f"{base}.zip"
    suffix = 2
    while candidate.exists():
        candidate = parent / f"{base} ({suffix}).zip"
        suffix += 1
    return candidate


def worker_merge_thread(folder: str) -> None:
    from audit_engine.services.pdf_merger import MergeError, merge_folder_to_zip

    try:
        root = Path(folder)
        merge_tracker.log("INFO", f"Reading {root.name}")

        def on_progress(pct, message=""):
            merge_tracker.pct = int(pct)
            if message:
                merge_tracker.progress_text = message

        destination = _zip_destination(root)
        result = merge_folder_to_zip(root, destination, on_progress=on_progress)

        merge_tracker.log(
            "OK",
            f"{result['branch_count']} branch(es), {result['total_sources']} source file(s), "
            f"{result['total_pages']} page(s)",
        )
        for note in result.get("notes", []):
            merge_tracker.log("WARN", note)
        merge_tracker.log("OK", f"Saved: {result['zip_path']}")

        result["zip_name"] = Path(result["zip_path"]).name
        result["zip_bytes"] = destination.stat().st_size if destination.exists() else 0
        merge_tracker.summary = result
        merge_tracker.pct = 100
        merge_tracker.progress_text = "Merge complete."
        merge_tracker.is_running = False

        from audit_engine.utils.platform import trigger_notification
        trigger_notification("Merge PDF", f"Merged {result['branch_count']} branch(es)")
    except MergeError as e:
        _fail(str(e))
    except FileNotFoundError as e:
        _fail(str(e))
    except Exception as e:  # noqa: BLE001 - nothing may escape the worker
        _fail(f"Unexpected error: {e}")


def _fail(message: str) -> None:
    merge_tracker.error_msg = message
    merge_tracker.log("ERROR", message)
    merge_tracker.progress_text = "Merge failed."
    merge_tracker.pct = 100
    merge_tracker.is_running = False


def handle_merge_run(data: dict) -> dict:
    data = data or {}
    folder = (data.get("folder") or "").strip()

    if not folder:
        return {"success": False, "error": "No folder selected."}
    if not os.path.isdir(folder):
        return {"success": False, "error": f"Folder not found: {folder}"}
    if merge_tracker.is_running:
        return {"success": False, "error": "A merge is already running."}

    merge_tracker.reset()
    threading.Thread(target=worker_merge_thread, args=(folder,), daemon=True).start()
    return {"success": True, "message": "Merge started."}


def handle_merge_progress() -> dict:
    return {
        "success": True,
        "is_running": merge_tracker.is_running,
        "pct": merge_tracker.pct,
        "progress_text": merge_tracker.progress_text,
        "logs": list(merge_tracker.logs),
        "summary": merge_tracker.summary or None,
        "error": merge_tracker.error_msg or None,
    }


def handle_merge_open(data: dict) -> dict:
    """Reveal the merged zip in the OS file manager."""
    path = ((data or {}).get("path") or "").strip()
    if not path or not os.path.exists(path):
        return {"success": False, "error": "Merged zip not found."}
    open_path(path)
    return {"success": True}
