#!/usr/bin/env python3
"""Audit Engine Elite — Entry point.

Uses the app factory (app.py) to bootstrap the application, then starts either:
1. A native desktop window via pywebview (preferred)
2. A local Bottle HTTP server + browser fallback
"""

import logging
import os
import socket
import subprocess
import threading
import time
import webbrowser

import audit_engine.ui as templates
from audit_engine._version import VERSION
from audit_engine.app import _ipc_mode, create_app, start_heartbeat_monitor
from audit_engine.lib.bottle import run
from audit_engine.web.bridge import WebViewBridge

logger = logging.getLogger(__name__)


def find_free_port(start_port: int = 52140) -> int:
    for port in range(start_port, start_port + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start_port


def open_browser(port: int) -> None:
    import platform
    time.sleep(0.6)
    url = f"http://localhost:{port}"
    system = platform.system()

    if system == "Windows":
        for browser_path in [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        ]:
            if os.path.exists(browser_path):
                subprocess.Popen([browser_path, "--proxy-bypass-list=localhost,127.0.0.1", "--app=" + url])
                return
    elif system == "Darwin":
        mac_chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        if os.path.exists(mac_chrome):
            subprocess.Popen([mac_chrome, "--proxy-bypass-list=localhost,127.0.0.1", "--app=" + url])
            return
    elif system == "Linux":
        for cmd in ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"]:
            import shutil
            if shutil.which(cmd):
                subprocess.Popen([cmd, "--proxy-bypass-list=localhost,127.0.0.1", "--app=" + url])
                return

    webbrowser.open(url)


def main() -> None:
    import multiprocessing
    multiprocessing.freeze_support()

    # Bootstrap application
    create_app()

    # Try pywebview native window first
    try:
        import webview

        logger.info("Launching native desktop window using pywebview (Zero-Socket IPC Mode)...")
        _ipc_mode.enabled = True
        bridge = WebViewBridge()

        html = templates.get_html(VERSION)
        temp_path = os.path.expanduser("~/.audit_engine_ui.html")
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(html)

        webview.create_window("Audit Engine", url="file://" + temp_path, js_api=bridge, width=1200, height=800)
        webview.start()
    except Exception as e:
        import traceback
        try:
            err_path = os.path.expanduser("~/Desktop/webview_error.txt")
            with open(err_path, "w") as f:
                f.write(f"PyWebView Error: {e}\n{traceback.format_exc()}")
        except Exception:
            pass

        logger.warning("PyWebView failed: %s. Falling back to browser UI.", e)

        port = find_free_port()
        start_heartbeat_monitor()
        threading.Thread(target=open_browser, args=(port,), daemon=True).start()
        logger.info("Audit Engine listening on http://localhost:%d", port)
        run(host="localhost", port=port, quiet=True)


if __name__ == "__main__":
    main()
