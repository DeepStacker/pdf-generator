"""File and directory dialog helpers with PyWebView + Tkinter subprocess fallback."""

import json
import subprocess
import sys
from typing import Any

from audit_engine.utils.platform import file_logger


def _tkinter_startupinfo() -> Any | None:
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        return startupinfo
    return None


def _run_tkinter_subprocess(script: str) -> str:
    cmd = [sys.executable, "-c", script]
    startupinfo = _tkinter_startupinfo()
    res = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo, check=True)
    return res.stdout.strip()


def ask_file_dialog() -> str:
    try:
        import webview
        active_win = webview.active_window()
        if not active_win and hasattr(webview, "windows") and webview.windows:
            active_win = webview.windows[0]
        if active_win:
            file_types = (
                'Excel Files (*.xlsx;*.xls;*.xlsm;*.XLSX;*.XLS;*.XLSM)',
                'All files (*.*)'
            )
            result = active_win.create_file_dialog(
                dialog_type=webview.OPEN_DIALOG,
                file_types=file_types
            )
            if result:
                return str(result[0]) if isinstance(result, (list, tuple)) else str(result)
            return ""
    except Exception as e:
        file_logger.info(f"PyWebView native file dialog not active or not available: {e}")

    try:
        script = (
            "import tkinter as tk; from tkinter import filedialog; "
            "root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True); "
            "path = filedialog.askopenfilename(title='Select Master Excel File', "
            "filetypes=[('Excel Files', '*.xlsx *.xls *.XLSX *.XLS *.xlsm *.XLSM'), ('All Files', '*')]); "
            "print(path)"
        )
        return _run_tkinter_subprocess(script)
    except Exception as te:
        file_logger.warning(f"Subprocess Tkinter file dialog fallback failed: {te}")
        return ""


def ask_files_dialog() -> list[str]:
    try:
        import webview
        active_win = webview.active_window()
        if not active_win and hasattr(webview, "windows") and webview.windows:
            active_win = webview.windows[0]
        if active_win:
            file_types = (
                'Excel Files (*.xlsx;*.xls;*.xlsm;*.XLSX;*.XLS;*.XLSM)',
                'All files (*.*)'
            )
            result = active_win.create_file_dialog(
                dialog_type=webview.OPEN_DIALOG,
                file_types=file_types,
                allow_multiple=True
            )
            if result:
                if isinstance(result, (list, tuple)):
                    return [str(x) for x in result]
                return [str(result)]
            return []
    except Exception as e:
        file_logger.info(f"PyWebView native multiple files dialog not active or not available: {e}")

    try:
        script = (
            "import tkinter as tk; from tkinter import filedialog; import json; "
            "root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True); "
            "paths = filedialog.askopenfilenames(title='Select Master Excel Files', "
            "filetypes=[('Excel Files', '*.xlsx *.xls *.XLSX *.XLS *.xlsm *.XLSM'), ('All Files', '*')]); "
            "print(json.dumps(paths))"
        )
        paths_str = _run_tkinter_subprocess(script)
        if paths_str:
            return json.loads(paths_str)
        return []
    except Exception as te:
        file_logger.warning(f"Subprocess Tkinter multiple files dialog fallback failed: {te}")
        return []


def ask_directory_dialog() -> str:
    try:
        import webview
        active_win = webview.active_window()
        if not active_win and hasattr(webview, "windows") and webview.windows:
            active_win = webview.windows[0]
        if active_win:
            result = active_win.create_file_dialog(
                dialog_type=webview.FOLDER_DIALOG
            )
            if result:
                return str(result[0]) if isinstance(result, (list, tuple)) else str(result)
            return ""
    except Exception as e:
        file_logger.info(f"PyWebView native directory dialog not active or not available: {e}")

    try:
        script = (
            "import tkinter as tk; from tkinter import filedialog; "
            "root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True); "
            "path = filedialog.askdirectory(title='Select Output Directory'); "
            "print(path)"
        )
        return _run_tkinter_subprocess(script)
    except Exception as te:
        file_logger.warning(f"Subprocess Tkinter directory dialog fallback failed: {te}")
        return ""
