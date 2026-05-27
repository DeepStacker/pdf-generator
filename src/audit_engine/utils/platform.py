"""Platform utilities: file opening, desktop notifications, logging setup.

All operations are designed to work without admin privileges and fail
gracefully in locked-down corporate environments (Sophos, etc.).
"""

import logging
import os
import subprocess
import sys

from audit_engine.utils.config import paths


def setup_logging() -> logging.Logger:
    """Set up file logging with graceful fallback.

    If the configured log path is not writable (e.g., restricted directory),
    logging silently falls back to console-only mode.
    """
    logger = logging.getLogger("audit_engine")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    try:
        log_dir = os.path.dirname(paths.log)
        if log_dir and not os.path.isdir(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        handler = logging.FileHandler(paths.log, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(handler)
    except (OSError, PermissionError):
        # Log file not writable — fall back to NullHandler (no crash)
        logger.addHandler(logging.NullHandler())
    return logger


file_logger: logging.Logger = setup_logging()


def open_path(path: str) -> None:
    """Open a file or folder in the system's default handler.

    Uses platform-native mechanisms that don't require admin privileges:
    - Windows: os.startfile() (no elevation needed)
    - macOS: /usr/bin/open (standard user tool)
    - Linux: xdg-open (desktop standard)
    """
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
    except OSError as e:
        file_logger.warning(f"Failed to open path: {path} — {e}")


def trigger_notification(title: str, message: str) -> None:
    """Trigger a native desktop notification.

    Uses platform-native notification mechanisms. Fails silently if
    blocked by corporate policy or antivirus (Sophos, etc.).
    On Windows, uses PowerShell (available to standard users).
    On macOS, uses osascript (available to standard users).
    """
    try:
        if sys.platform == "darwin":
            safe_msg = message.replace('"', '\\"').replace("'", "\\'")
            safe_title = title.replace('"', '\\"').replace("'", "\\'")
            cmd = ["osascript", "-e", f'display notification "{safe_msg}" with title "{safe_title}"']
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        elif sys.platform == "win32":
            safe_title = title.replace("`", "``").replace("'", "`'").replace('"', '`"')
            safe_msg = message.replace("`", "``").replace("'", "`'").replace('"', '`"')
            ps_script = (
                'Add-Type -AssemblyName System.Windows.Forms;'
                '$n = New-Object System.Windows.Forms.NotifyIcon;'
                '$n.Icon = [System.Drawing.SystemIcons]::Information;'
                f'$n.BalloonTipIcon = "Info";'
                f'$n.BalloonTipTitle = "{safe_title}";'
                f'$n.BalloonTipText = "{safe_msg}";'
                '$n.Visible = $True;'
                '$n.ShowBalloonTip(5000)'
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
    except Exception as ne:
        file_logger.warning(f"Failed to trigger desktop notification: {ne}")
