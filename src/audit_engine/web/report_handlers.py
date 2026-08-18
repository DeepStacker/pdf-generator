"""Report Validator handlers for the desktop app — fully offline, zero-socket.

The web server validates *uploaded bytes* (multipart in, file stream out). The
desktop app cannot do that: its JS talks to Python through the in-process
WebViewBridge, which passes JSON strings only — no multipart body, no binary
response. It does not need to either, because a desktop user already has the
file on disk.

So this module is path-based end to end:

    native file dialog -> absolute path -> validate in place -> write the
    result beside the source -> reveal it in the OS file manager

Nothing here opens a socket, resolves a host, or writes a temp upload, which is
what lets the packaged desktop build run in fully network-restricted
environments. The actual validation is the same shared core the web server
calls (audit_engine.services.report_validator.validate_workbook).
"""

import os
import threading

from audit_engine.utils.dialogs import ask_file_dialog, ask_pdf_file_dialog
from audit_engine.utils.platform import open_path


class _ReportTracker:
    """State for the single in-flight desktop validation job.

    One job at a time, mirroring how the Bank Audit and Consolidation tabs
    already behave. Attributes are written by the worker thread and read by
    the polling thread; each is a plain assignment of an immutable value, so
    reads are consistent without locking (same approach as _ConsolidationTracker).
    """

    def __init__(self) -> None:
        self.is_running: bool = False
        self.pct: int = 0
        self.progress_text: str = "Ready. Select a report to validate."
        self.summary: dict = {}
        self.error_msg: str = ""
        self.logs: list[dict] = []

    def reset(self) -> None:
        self.is_running = True
        self.pct = 0
        self.progress_text = "Starting validation..."
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


report_tracker = _ReportTracker()


def handle_report_browse() -> dict:
    """Native picker for the report workbook."""
    path = ask_file_dialog()
    return {"success": True, "path": path or ""}


def handle_report_browse_pdf() -> dict:
    """Native picker for the optional sequence PDF."""
    path = ask_pdf_file_dialog()
    return {"success": True, "path": path or ""}


def worker_report_thread(filepath: str, pdf_path: str | None) -> None:
    from audit_engine.services.report_validator import validate_workbook

    try:
        report_tracker.log("INFO", f"Reading {os.path.basename(filepath)}")
        if pdf_path:
            report_tracker.log("INFO", f"Sequence PDF: {os.path.basename(pdf_path)}")
        else:
            report_tracker.log("INFO", "No PDF supplied - row order left unchanged")

        def on_progress(pct, msg=None):
            report_tracker.pct = int(pct)
            if msg:
                report_tracker.progress_text = msg

        # output_path omitted -> writes "<BRANCH>_Audit-MIS_<dates>.xlsx"
        # beside the source file.
        result = validate_workbook(filepath, pdf_path=pdf_path or None, on_progress=on_progress)

        total = result.get("total_issues", 0)
        if result.get("pdf_warning"):
            report_tracker.log("WARN", result["pdf_warning"])
        elif pdf_path and result.get("pdf_applied"):
            report_tracker.log(
                "OK", f"Rows resequenced to match the PDF ({result.get('pdf_matched_rows', 0)} matched)"
            )
        report_tracker.log("OK", f"Validation complete - {total} issue(s) flagged")
        report_tracker.log("OK", f"Saved: {result.get('output_path', '')}")

        report_tracker.summary = result
        report_tracker.pct = 100
        report_tracker.progress_text = "Validation complete."
        report_tracker.is_running = False

        from audit_engine.utils.platform import trigger_notification
        trigger_notification("Report Validator", f"{total} issue(s) flagged in {os.path.basename(filepath)}")
    except FileNotFoundError as e:
        _fail(str(e))
    except KeyError as e:
        # validate_workbook raises KeyError with the available sheet names.
        _fail(str(e).strip('"'))
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "zipfile" in msg.lower() or "not a zip" in msg.lower():
            msg = "Invalid or corrupt .xlsx file."
        _fail(msg)


def _fail(message: str) -> None:
    report_tracker.error_msg = message
    report_tracker.log("ERROR", message)
    report_tracker.progress_text = "Validation failed."
    report_tracker.pct = 100
    report_tracker.is_running = False


def handle_report_run(data: dict) -> dict:
    data = data or {}
    filepath = (data.get("filepath") or "").strip()
    pdf_path = (data.get("pdf_path") or "").strip()

    if not filepath:
        return {"success": False, "error": "No report file selected."}
    if not os.path.exists(filepath):
        return {"success": False, "error": f"File not found: {filepath}"}
    if not filepath.lower().endswith(".xlsx"):
        return {"success": False, "error": "Only .xlsx files are supported (.xls is not)."}
    # The PDF is optional; a stale/missing path is ignored rather than fatal.
    if pdf_path and not os.path.exists(pdf_path):
        pdf_path = ""
    if report_tracker.is_running:
        return {"success": False, "error": "A validation is already running."}

    report_tracker.reset()
    threading.Thread(
        target=worker_report_thread,
        args=(filepath, pdf_path or None),
        daemon=True,
    ).start()

    return {"success": True, "message": "Validation started."}


def handle_report_progress() -> dict:
    return {
        "success": True,
        "is_running": report_tracker.is_running,
        "pct": report_tracker.pct,
        "progress_text": report_tracker.progress_text,
        "logs": list(report_tracker.logs),
        "summary": report_tracker.summary or None,
        "error": report_tracker.error_msg or None,
    }


def handle_report_open(data: dict) -> dict:
    """Reveal the validated workbook in the OS file manager.

    This replaces the web build's HTTP download: the file is already on the
    user's disk, so nothing needs to cross the bridge.
    """
    path = ((data or {}).get("path") or "").strip()
    if not path or not os.path.exists(path):
        return {"success": False, "error": "Output file not found."}
    open_path(path)
    return {"success": True}
