#!/usr/bin/env python3
"""Audit Engine Elite — Entry point.

Uses the app factory (app.py) to bootstrap the application, then launches
a native desktop window via pywebview (Zero-Socket IPC Mode).

This is the ONLY supported mode. No localhost HTTP server is started —
the app works entirely without network access, making it compatible with
locked-down corporate environments where localhost/127.0.0.1 is blocked.
"""

import logging
import os
import sys
import tempfile

import audit_engine.ui as templates
from audit_engine._version import VERSION
from audit_engine.app import _ipc_mode, create_app
from audit_engine.web.bridge import WebViewBridge

logger = logging.getLogger(__name__)


def _is_unsafe_vm_or_net_path(path: str) -> bool:
    """Check if a path is on an unsafe VM shared folder or network share.

    SQLite has locking/I/O issues on network drives and shared filesystems.
    Windows WebViews block script execution from UNC paths.
    """
    path_lower = path.lower()
    if path.startswith(("\\\\", "//")):
        return True
    if "/media/psf" in path_lower or "/mnt/psf" in path_lower or "prl_fs" in path_lower:
        return True
    return False


def _get_writable_temp_dir() -> str:
    """Return a writable temporary directory, with multiple fallback locations.

    Corporate environments may restrict temp directories. Try in order:
    1. Local platform-specific application data directory (guaranteed local to guest OS/VM)
    2. System temp directory (always writable for standard users)
    3. User's home directory
    4. Directory next to the executable (for portable mode)
    """
    candidates = []

    # 1. Platform-specific local app data directory
    if sys.platform == "win32":
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            candidates.append(os.path.join(local_appdata, "AuditEngineElite"))
        appdata = os.environ.get("APPDATA")
        if appdata:
            candidates.append(os.path.join(appdata, "AuditEngineElite"))
    elif sys.platform == "darwin":
        home = os.path.expanduser("~")
        if home:
            candidates.append(os.path.join(home, "Library", "Application Support", "AuditEngineElite"))
    else:
        home = os.path.expanduser("~")
        if home:
            candidates.append(os.path.join(home, ".local", "share", "AuditEngineElite"))

    # 2. System temp directory
    candidates.append(tempfile.gettempdir())

    # 3. User's home directory
    candidates.append(os.path.expanduser("~"))

    # 4. For frozen PyInstaller binaries, also try the executable's directory
    if getattr(sys, "frozen", False):
        candidates.append(os.path.dirname(sys.executable))

    for candidate in candidates:
        if candidate and not _is_unsafe_vm_or_net_path(candidate):
            try:
                os.makedirs(candidate, exist_ok=True)
                if os.path.isdir(candidate) and os.access(candidate, os.W_OK):
                    return candidate
            except Exception:
                continue

    # Last resort — should never reach here
    return tempfile.gettempdir()


def _path_to_file_uri(path: str) -> str:
    """Convert a filesystem path to a proper file:// URI across all platforms.

    Windows: C:\\Users\\foo\\bar.html  →  file:///C:/Users/foo/bar.html
    macOS:   /Users/foo/bar.html      →  file:///Users/foo/bar.html
    Linux:   /home/foo/bar.html       →  file:///home/foo/bar.html
    """
    from pathlib import Path
    return Path(path).as_uri()


def _show_fatal_error(message: str) -> None:
    """Show a fatal error dialog using Tkinter (always bundled with PyInstaller).

    This is the last-resort UI when pywebview cannot launch.
    Tkinter does not require any network access or admin privileges.
    """
    logger.error("Fatal: %s", message)
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        messagebox.showerror(
            "Audit Engine Elite — Startup Error",
            f"{message}\n\n"
            "The application requires pywebview to run.\n"
            "Please contact your IT administrator if this error persists.",
        )
        root.destroy()
    except Exception:
        # If even Tkinter fails, write error to a writable location as last resort
        for err_dir in [_get_writable_temp_dir(), os.path.expanduser("~")]:
            if _is_unsafe_vm_or_net_path(err_dir):
                continue
            try:
                err_path = os.path.join(err_dir, "audit_engine_error.txt")
                with open(err_path, "w") as f:
                    f.write(f"Audit Engine Elite — Startup Error\n\n{message}\n")
                break
            except Exception:
                continue


def main() -> None:
    import multiprocessing
    multiprocessing.freeze_support()

    # Bootstrap application (database, logging, routes)
    create_app()

    # Launch native desktop window via pywebview (Zero-Socket IPC Mode)
    try:
        import webview

        logger.info("Launching native desktop window using pywebview (Zero-Socket IPC Mode)...")
        _ipc_mode.enabled = True
        bridge = WebViewBridge()

        html = templates.get_html(VERSION)
        temp_dir = _get_writable_temp_dir()
        temp_path = os.path.join(temp_dir, "audit_engine_ui.html")
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(html)

        file_uri = _path_to_file_uri(temp_path)
        logger.info("Loading UI from: %s", file_uri)

        webview.create_window(
            "Audit Engine Elite",
            url=file_uri,
            js_api=bridge,
            width=1200,
            height=800,
        )
        webview.start()
    except ImportError:
        _show_fatal_error(
            "PyWebView module is not available.\n\n"
            "This usually means the application bundle is incomplete.\n"
            "Please re-download the latest release from GitHub."
        )
    except Exception as e:
        import traceback

        error_detail = f"{e}\n\n{traceback.format_exc()}"
        logger.error("PyWebView launch failed: %s", error_detail)
        _show_fatal_error(f"Failed to launch the application window:\n\n{e}")
    finally:
        # Clean up temp HTML file on exit
        try:
            temp_dir = _get_writable_temp_dir()
            temp_path = os.path.join(temp_dir, "audit_engine_ui.html")
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass


if __name__ == "__main__":
    main()
