#!/usr/bin/env python3
"""Audit Engine Elite v5 — GUI Application

Professional-grade PDF report generator for IDFC FIRST Bank & Equitas Small Finance Bank gold-loan audits.
Reads Excel master files, groups records by branch, and produces audit worksheets.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import threading
import os
import sys
import subprocess
import queue
import zipfile
import sqlite3
import logging
from datetime import datetime
import openpyxl

# Import core logic modules
import pdf_logic
import equitas_logic


# =========================================================
# VERSION & APP CONSTANTS
# =========================================================
VERSION = "5.2.127"
APP_TITLE = "Audit Engine v5.0"

# Colors for theming
THEME = {
    "IDFC First Bank": {
        "primary": "#2563EB",  # Blue
        "primary_hover": "#1D4ED8",
        "secondary": "#FFFFFF",
        "text": "#0F172A",
    },
    "Equitas Small Finance Bank": {
        "primary": "#D97706",  # Orange/Amber
        "primary_hover": "#B45309",
        "secondary": "#FFFFFF",
        "text": "#0F172A",
    }
}


# =========================================================
# FILE LOGGING
# =========================================================
LOG_FILE = os.path.join(os.path.expanduser("~"), ".idfc_audit_engine.log")
file_logger = logging.getLogger("audit_engine")
file_logger.setLevel(logging.INFO)
try:
    _fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    file_logger.addHandler(_fh)
except OSError:
    pass  # Non-critical — file logging unavailable


# =========================================================
# PLATFORM UTILITIES
# =========================================================
def open_path(path):
    """Open a file or folder in the system's default handler."""
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
    except OSError as e:
        file_logger.warning(f"Failed to open path: {path} — {e}")


# =========================================================
# DATABASE HANDLING
# =========================================================
DB_PATH = os.path.join(os.path.expanduser("~"), ".idfc_pdf_generator_v3.db")

def _connect_db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = _connect_db()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS history
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      timestamp TEXT,
                      excel_name TEXT,
                      pdf_count INTEGER,
                      output_path TEXT,
                      audit_type TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS config
                     (key TEXT PRIMARY KEY, value TEXT)''')
    try:
        cursor.execute("ALTER TABLE history ADD COLUMN full_path TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

def set_config(key, value):
    conn = _connect_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def get_config(key, default=None):
    conn = _connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else default

def log_generation(excel_name, pdf_count, output_path, audit_type, full_path=None):
    conn = _connect_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO history (timestamp, excel_name, pdf_count, output_path, audit_type, full_path) VALUES (?, ?, ?, ?, ?, ?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), excel_name, pdf_count, output_path, audit_type, full_path)
    )
    conn.commit()
    conn.close()

def get_stats():
    conn = _connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), SUM(pdf_count) FROM history")
    res = cursor.fetchone()
    conn.close()
    return (res[0] or 0, res[1] or 0)

def get_analytics():
    conn = _connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT audit_type, COUNT(*) FROM history GROUP BY audit_type")
    types = dict(cursor.fetchall())
    cursor.execute("SELECT strftime('%Y-%m-%d', timestamp), COUNT(*) FROM history GROUP BY 1 ORDER BY 1 DESC LIMIT 7")
    trend = cursor.fetchall()
    conn.close()
    return types, trend

def get_recent_history(search="", limit=100):
    conn = _connect_db()
    cursor = conn.cursor()
    if search:
        cursor.execute(
            "SELECT id, timestamp, excel_name, pdf_count, output_path, audit_type, full_path FROM history WHERE excel_name LIKE ? ORDER BY id DESC LIMIT ?",
            (f"%{search}%", limit)
        )
    else:
        cursor.execute(
            "SELECT id, timestamp, excel_name, pdf_count, output_path, audit_type, full_path FROM history ORDER BY id DESC LIMIT ?",
            (limit,)
        )
    res = cursor.fetchall()
    conn.close()
    return res

init_db()


# =========================================================
# SCROLLABLE FRAME WIDGET
# =========================================================
# =========================================================
# TOOLTIP WIDGET
# =========================================================
class ToolTip:
    def __init__(self, widget, text, delay=400):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tip_window = None
        self._after_id = None
        widget.bind("<Enter>", self.schedule)
        widget.bind("<Leave>", self.hide)

    def schedule(self, event=None):
        self._after_id = self.widget.after(self.delay, self.show)

    def show(self):
        if self.tip_window:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=self.text, justify=tk.LEFT,
                 background="#1E293B", foreground="#F8FAFC",
                 font=("Inter", 9), padx=12, pady=6,
                 wraplength=350).pack()

    def hide(self, event=None):
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


# =========================================================
# LOG LEVEL COLORS (for color-coded console)
# =========================================================
LOG_COLORS = {
    "INFO": "#10B981",     # green
    "OK": "#10B981",       # green
    "WARN": "#F59E0B",     # amber
    "ERROR": "#EF4444",    # red
    "DEBUG": "#64748B",    # slate
}


# =========================================================
# AUTO-UPDATER
# =========================================================
UPDATE_REPO = "DeepStacker/pdf-generator"
GITHUB_API = f"https://api.github.com/repos/{UPDATE_REPO}/releases/latest"

import urllib.request as _urllib
import urllib.error as _urlerror
import json as _json
import tempfile as _tempfile
import shutil as _shutil
import ssl as _ssl


def _make_ssl_context():
    """Create SSL context using certifi CA bundle if available."""
    try:
        import certifi
        cafile = certifi.where()
        if os.path.exists(cafile):
            return _ssl.create_default_context(cafile=cafile)
    except Exception:
        pass
    return _ssl.create_default_context()


def _urlopen_with_fallback(req, timeout=10):
    """Open a URL with SSL fallback: certifi → system → unverified (last resort)."""
    try:
        ctx = _make_ssl_context()
        return _urllib.urlopen(req, context=ctx, timeout=timeout)
    except _urlerror.URLError as e:
        if "CERTIFICATE_VERIFY_FAILED" in str(e):
            print("WARNING: SSL verification failed; retrying without verification.")
            ctx = _ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = _ssl.CERT_NONE
            return _urllib.urlopen(req, context=ctx, timeout=timeout)
        raise


def _get_platform_suffix():
    """Return the platform string used in binary ZIP filenames."""
    if sys.platform == "darwin":
        return "macos"
    elif sys.platform == "win32":
        return "windows"
    return "linux"


def _check_latest_release():
    """Check GitHub for the latest release. Returns (tag, source_url, body, binary_url)."""
    req = _urllib.Request(GITHUB_API, headers={"User-Agent": f"AuditEngine/{VERSION}"})
    with _urlopen_with_fallback(req, timeout=10) as resp:
        data = _json.loads(resp.read().decode())
    tag = data["tag_name"]
    source_url = data["zipball_url"]
    body = data.get("body", "")
    suffix = f"binary_{_get_platform_suffix()}.zip"
    binary_url = ""
    for asset in data.get("assets", []):
        if suffix in asset["name"] and asset["name"].endswith(".zip"):
            binary_url = asset["browser_download_url"]
            break
    return tag, source_url, body, binary_url


def _parse_version(tag):
    """Parse version tag like 'v5.1.0' into tuple (5, 1, 0)."""
    return tuple(int(x) for x in tag.lstrip("vV").split("."))


def _download_update(url, dest_path, progress_callback=None):
    """Download a file with optional progress callback (0-100)."""
    req = _urllib.Request(url, headers={"User-Agent": f"AuditEngine/{VERSION}"})
    with _urlopen_with_fallback(req, timeout=60) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        with open(dest_path, "wb") as f:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback and total:
                    progress_callback(downloaded / total * 100)
    return dest_path


def _install_update(zip_path, install_dir, log_callback=print):
    """Extract a GitHub source zipball over the install directory."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        members = zf.infolist()
        prefix = members[0].filename if members else ""
        for m in members:
            rel = m.filename[len(prefix):] if prefix else m.filename
            if not rel or m.is_dir():
                if rel and rel.strip("/"):
                    os.makedirs(os.path.join(install_dir, rel), exist_ok=True)
                continue
            dest = os.path.join(install_dir, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f:
                f.write(zf.read(m))
    log_callback(f"Update extracted to {install_dir}")


def _install_binary_update(zip_path, install_dir, log_callback=print):
    """Extract a platform-specific binary ZIP over the running executable.

    On Windows (frozen), this creates a batch script that:
      1. Waits for the current process to exit cleanly
      2. Waits extra time for PyInstaller _MEI temp dir cleanup
      3. Copies the new exe over the old one (with retries)
      4. Cleans up stale _MEI temp directories
      5. Launches the updated application
      6. Cleans up the staging directory

    Returns the path to the batch script on Windows (caller must exit
    cleanly via sys.exit so atexit handlers run and _MEI is released),
    or None on other platforms (update applied in-place).
    """
    import shutil
    import stat
    import subprocess
    extract_to = _tempfile.mkdtemp(prefix="audit_bin_")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_to)
    # Promote permissions so we can find and run the binary
    for root, dirs, files in os.walk(extract_to):
        for f in files:
            fp = os.path.join(root, f)
            st = os.stat(fp)
            os.chmod(fp, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    src = None
    for root, dirs, files in os.walk(extract_to):
        for f in files:
            fp = os.path.join(root, f)
            if os.access(fp, os.X_OK):
                src = fp
                break
        if src:
            break
    if not src:
        raise RuntimeError("No executable found in update ZIP")
    old_exe = sys.executable
    log_callback(f"Replacing {old_exe} with {src}")
    if sys.platform == "win32":
        # Windows: can't rename/overwrite a running exe directly.
        # Stage the new exe and create a batch script to perform the swap
        # AFTER this process exits cleanly (so _MEI temp dir is released).
        new_exe = os.path.join(extract_to, os.path.basename(old_exe))
        if src != new_exe:
            shutil.copy2(src, new_exe)
        bat_path = os.path.join(extract_to, "_update.bat")
        # Batch script: wait for parent → retry copy → clean _MEI → launch → cleanup
        bat_contents = (
            "@echo off\r\n"
            "REM === Audit Engine Auto-Update Script ===\r\n"
            "REM Wait for the parent process to exit cleanly\r\n"
            ":wait_exit\r\n"
            'tasklist /fi "PID eq %PARENT_PID%" 2>nul | find "%PARENT_PID%" >nul\r\n'
            "if not errorlevel 1 (\r\n"
            "  timeout /t 1 /nobreak >nul\r\n"
            "  goto wait_exit\r\n"
            ")\r\n"
            "REM Extra wait for PyInstaller _MEI temp dir cleanup\r\n"
            "timeout /t 3 /nobreak >nul\r\n"
            "REM Copy new exe over old with retry (antivirus may briefly lock)\r\n"
            "set RETRIES=0\r\n"
            ":retry_copy\r\n"
            'copy /y "' + new_exe.replace('/', '\\') + '" "' + old_exe.replace('/', '\\') + '" >nul 2>&1\r\n'
            "if errorlevel 1 (\r\n"
            "  set /a RETRIES+=1\r\n"
            "  if %RETRIES% lss 10 (\r\n"
            "    timeout /t 2 /nobreak >nul\r\n"
            "    goto retry_copy\r\n"
            "  )\r\n"
            "  REM Copy failed after retries — launch old exe anyway\r\n"
            ")\r\n"
            "REM Clean up stale _MEI temp directories from previous runs\r\n"
            'for /d %%D in ("%TEMP%\\_MEI*") do rd /s /q "%%D" 2>nul\r\n'
            "REM Launch the updated application\r\n"
            'start "" "' + old_exe.replace('/', '\\') + '"\r\n'
            "REM Clean up staging directory and self-delete\r\n"
            'rd /s /q "' + extract_to.replace('/', '\\') + '" 2>nul\r\n'
        )
        with open(bat_path, "w") as f:
            f.write(bat_contents)
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0  # SW_HIDE
        subprocess.Popen(
            ["cmd.exe", "/c", bat_path],
            env={**os.environ, "PARENT_PID": str(os.getpid())},
            close_fds=True,
            startupinfo=startup,
        )
        log_callback("Update staged; batch script launched. Waiting for clean exit.")
        return bat_path  # Signal caller that a batch script is handling the restart
    # macOS / Linux: replace in-place
    backup = old_exe + ".bak"
    if os.path.exists(old_exe):
        os.rename(old_exe, backup)
    os.makedirs(os.path.dirname(old_exe), exist_ok=True)
    shutil.copy2(src, old_exe)
    os.chmod(old_exe, 0o755)
    # Remove quarantine attribute so next launch doesn't trigger Gatekeeper
    if sys.platform == "darwin":
        subprocess.run(["xattr", "-dr", "com.apple.quarantine", old_exe], check=False)
    if os.path.exists(backup):
        os.remove(backup)
    shutil.rmtree(extract_to, ignore_errors=True)
    log_callback(f"Binary updated at {old_exe}")
    return None


def _get_install_dir():
    """Return the directory where the application is installed."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _cleanup_stale_mei():
    """Remove orphaned _MEI* temp directories from previous PyInstaller crashes.

    When the app is killed via os._exit() or crashes, PyInstaller's atexit
    handler doesn't run and the _MEI extraction directory is left behind.
    This cleans those up on the next launch.
    """
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return
    try:
        temp_dir = _tempfile.gettempdir()
        current_mei = getattr(sys, '_MEIPASS', '')
        current_mei_name = os.path.basename(current_mei).lower() if current_mei else ""
        for entry in os.listdir(temp_dir):
            if not entry.startswith('_MEI'):
                continue
            
            # Compare basenames (folder names) to avoid Windows short/long path mismatch
            # e.g. C:\Users\DEEPST~1\... vs C:\Users\DeepStacker\...
            if entry.lower() == current_mei_name:
                continue
            
            mei_path = os.path.join(temp_dir, entry)
            if not os.path.isdir(mei_path):
                continue
            try:
                _shutil.rmtree(mei_path)
            except (PermissionError, OSError):
                pass  # Still locked by another instance — skip
    except Exception:
        pass


def _restart_app():
    """Restart the application, replacing the current process.

    Uses sys.exit(0) on Windows instead of os._exit(0) so that
    PyInstaller's atexit handlers can clean up the _MEI temp directory.
    """
    import subprocess
    if sys.platform == "win32":
        subprocess.Popen([sys.executable] + (sys.argv if not getattr(sys, "frozen", False) else []))
        # sys.exit allows atexit handlers to run (PyInstaller _MEI cleanup)
        sys.exit(0)
    if getattr(sys, "frozen", False):
        os.execl(sys.executable, sys.executable)
    else:
        os.execl(sys.executable, sys.executable, *sys.argv)


class ScrollableFrame(tk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, bg=kwargs.get("bg", "#F8FAFC"), highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=kwargs.get("bg", "#F8FAFC"), padx=40, pady=30)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.scrollable_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)
        self.update_scrollbar_visibility()

    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.update_scrollbar_visibility()

    def update_scrollbar_visibility(self):
        self.canvas.update_idletasks()
        canvas_h = self.canvas.winfo_height()
        frame_h = self.scrollable_frame.winfo_reqheight()
        if frame_h > canvas_h:
            if not self.scrollbar.winfo_ismapped():
                self.scrollbar.pack(side="right", fill="y")
        else:
            if self.scrollbar.winfo_ismapped():
                self.scrollbar.pack_forget()

    def _bind_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        try:
            widget = self.canvas.winfo_containing(event.x_root, event.y_root)
            if widget:
                w_class = widget.winfo_class()
                if "Text" in w_class or "Listbox" in w_class or "Treeview" in w_class:
                    return
        except (tk.TclError, AttributeError):
            pass

        if sys.platform == "darwin":
            if abs(event.delta) >= 120:
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            else:
                self.canvas.yview_scroll(int(-1 * event.delta), "units")
        elif event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


# =========================================================
# MAIN APPLICATION
# =========================================================
# Recent files helpers
MAX_RECENT_FILES = 8

# Bank auto-detection column fingerprints
IDFC_FINGERPRINT_COLS = {"prospectno", "cuid", "tare weight", "currentbranch"}
EQUITAS_FINGERPRINT_COLS = {"svs_loan_no", "sole_id", "branch_name", "loan no"}

def _detect_bank_from_file(filepath):
    """Peek at Excel headers to determine which bank the file is for."""
    try:
        wb = openpyxl.load_workbook(filepath, data_only=True, read_only=True)
        try:
            for sname in wb.sheetnames:
                ws = wb[sname]
                try:
                    header_row = [
                        str(cell.value).strip().lower().replace("\n", "") if cell.value else ""
                        for cell in next(ws.iter_rows(min_row=1, max_row=1))
                    ]
                    headers_set = set(header_row)
                    idfc_score = len(IDFC_FINGERPRINT_COLS & headers_set)
                    equitas_score = len(EQUITAS_FINGERPRINT_COLS & headers_set)
                    if idfc_score >= 3:
                        return "IDFC First Bank"
                    if equitas_score >= 3:
                        return "Equitas Small Finance Bank"
                except StopIteration:
                    continue
        finally:
            wb.close()
    except Exception:
        pass
    return None

def _get_recent_files():
    files = []
    for i in range(MAX_RECENT_FILES):
        f = get_config(f"recent_file_{i}", "")
        if f and os.path.exists(f) and f not in files:
            files.append(f)
    return files

def _add_recent_file(filepath):
    files = _get_recent_files()
    filepath = os.path.abspath(os.path.normpath(filepath))
    files = [f for f in files if f != filepath]
    files.insert(0, filepath)
    files = files[:MAX_RECENT_FILES]
    for i, f in enumerate(files):
        set_config(f"recent_file_{i}", f)


class App:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)

        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except (ImportError, AttributeError, OSError):
                try:
                    import ctypes
                    ctypes.windll.user32.SetProcessDPIAware()
                except (ImportError, AttributeError, OSError):
                    pass

        try:
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            width = max(1020, min(1200, screen_w - 60))
            height = max(680, min(800, screen_h - 100))
            x = (screen_w - width) // 2
            y = (screen_h - height) // 2
            self.root.geometry(f"{width}x{height}+{x}+{y}")
        except (tk.TclError, ValueError):
            self.root.geometry("1150x780")

        self.root.configure(bg="#0F172A")

        try:
            if sys.platform in ("win32", "linux"):
                self.root.tk.call('tk', 'scaling', 1.25)
        except tk.TclError:
            pass

        # --- PERSISTENT STATE ---
        self.bank_var = tk.StringVar(value=get_config("bank", "IDFC First Bank"))
        last_file = get_config("last_file", "")
        self.file_var = tk.StringVar(value=last_file if os.path.exists(last_file) else "")
        self.file_var.trace_add("write", lambda *_: self._save_file_var())
        self.folder_var = tk.StringVar(value=get_config("out_path", os.path.join(os.path.expanduser("~"), "Desktop")))
        self.typ_var = tk.StringVar(value=get_config("audit_type", "POA"))
        self.auto_open = tk.BooleanVar(value=get_config("auto_open", "True") == "True")
        self.pkg_var = tk.StringVar(value=get_config("pkg_mode", "BOTH"))
        self.equitas_stage_var = tk.StringVar(value="STAGE 1")
        self.equitas_format_var = tk.StringVar(value=get_config("equitas_format", "BOTH"))
        self.equitas_pack_var = tk.StringVar(value=get_config("equitas_pack", "FOLDER"))

        self.progress_var = tk.DoubleVar(value=0)
        self.search_var = tk.StringVar()
        self.status_msg = tk.StringVar(value="Ready")

        # --- THREADING ---
        self.active_tab = "PROCESS"
        self.log_queue = queue.Queue()
        self.cancel_event = threading.Event()
        self._search_after_id = None

        self.search_var.trace_add("write", lambda *_: self._debounced_search())

        # Track pending update (batch script path on Windows)
        self._pending_update_bat = None

        self.setup_styles()
        self.setup_ui()
        self._setup_shortcuts()
        self.root.after(100, self.check_log_queue)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Clean up stale _MEI directories from previous crashed updates
        if getattr(sys, "frozen", False):
            threading.Thread(target=_cleanup_stale_mei, daemon=True).start()

        self.root.after(2000, self._check_updates_background)

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("Treeview",
                             background="#1E293B",
                             foreground="#F8FAFC",
                             fieldbackground="#1E293B",
                             rowheight=50,
                             font=("Inter", 10))
        self.style.configure("Treeview.Heading",
                             font=("Inter", 11, "bold"),
                             background="#334155",
                             foreground="#F8FAFC",
                             relief="flat")
        self.style.map("Treeview", background=[('selected', '#2563EB')])

        # Equitas specific styles
        self.style.map("TRadiobutton", background=[('active', '#FFFFFF')])

    def _setup_shortcuts(self):
        self.root.bind("<Control-o>", lambda e: self._shortcut_open())
        self.root.bind("<Control-O>", lambda e: self._shortcut_open())
        self.root.bind("<Control-R>", lambda e: self._shortcut_run())
        self.root.bind("<Control-r>", lambda e: self._shortcut_run())
        self.root.bind("<Return>", lambda e: self._shortcut_run())
        self.root.bind("<Escape>", lambda e: self._shortcut_cancel())
        self.root.bind("<Control-l>", lambda e: self._shortcut_clear_logs())
        self.root.bind("<Control-L>", lambda e: self._shortcut_clear_logs())

    def _shortcut_open(self):
        if self.active_tab != "PROCESS":
            self.switch_tab("PROCESS")
        if self.bank_var.get() == "IDFC First Bank":
            self.browse_in_idfc()
        else:
            stage = self.equitas_stage_var.get()
            if stage == "STAGE 1":
                self.browse_in_equitas_s1()
            else:
                self.browse_in_equitas_s2()

    def _shortcut_run(self):
        if self.active_tab != "PROCESS":
            return
        if self.btn_run.cget("state") != tk.DISABLED:
            if self.bank_var.get() == "IDFC First Bank":
                self.start_process_idfc()
            else:
                self.start_process_equitas()

    def _shortcut_cancel(self):
        if hasattr(self, 'btn_cancel') and self.btn_cancel.cget("state") != tk.DISABLED:
            self.cancel_process()

    def _save_file_var(self):
        path = self.file_var.get().strip()
        if path and os.path.exists(path):
            set_config("last_file", path)

    def _shortcut_clear_logs(self):
        if hasattr(self, 'log_area'):
            try:
                self.log_area.delete(1.0, tk.END)
                self.status_msg.set("Console cleared")
                self.root.after(2000, lambda: self.status_msg.set("Ready"))
            except (tk.TclError, AttributeError):
                pass

    def setup_ui(self):
        self.main_container = tk.Frame(self.root, bg="#0F172A")
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # Sidebar
        self.sidebar = tk.Frame(self.main_container, bg="#0F172A", width=280)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        # Logo Area
        logo_frame = tk.Frame(self.sidebar, bg="#0F172A", pady=25)
        logo_frame.pack(fill=tk.X)
        self.lbl_logo1 = tk.Label(logo_frame, font=("Inter", 22, "bold"), bg="#0F172A", fg="#FFFFFF")
        self.lbl_logo1.pack()
        self.lbl_logo2 = tk.Label(logo_frame, text="AUDIT ENGINE", font=("Inter", 9, "bold"), bg="#0F172A", fg="#2563EB", pady=5)
        self.lbl_logo2.pack()

        # Bank Selector
        bank_frame = tk.Frame(self.sidebar, bg="#0F172A", padx=20)
        bank_frame.pack(fill=tk.X, pady=(10, 20))
        tk.Label(bank_frame, text="BANK PROFILE", font=("Inter", 8, "bold"), bg="#0F172A", fg="#475569").pack(anchor="w", pady=(0, 5))
        self.bank_selector = ttk.Combobox(bank_frame, textvariable=self.bank_var, values=["IDFC First Bank", "Equitas Small Finance Bank"], state="readonly", font=("Inter", 10))
        self.bank_selector.pack(fill=tk.X)
        self.bank_selector.bind("<<ComboboxSelected>>", self.on_bank_change)
        ToolTip(self.bank_selector, "Switch between IDFC First Bank and Equitas Small Finance Bank workflows")

        # Navigation
        self.nav_btns = {}
        nav_items = [
            ("New Batch", "PROCESS"),
            ("Analytics", "STATS"),
            ("History", "HISTORY"),
            ("Settings", "SETTINGS"),
        ]

        nav_container = tk.Frame(self.sidebar, bg="#0F172A")
        nav_container.pack(fill=tk.X, expand=True, anchor="n")

        for label, tag in nav_items:
            self.nav_btns[tag] = self.create_nav_btn(label, tag, nav_container)

        # Footer
        footer = tk.Frame(self.sidebar, bg="#0F172A", pady=15)
        footer.pack(side=tk.BOTTOM, fill=tk.X)
        tk.Label(footer, text=f"v{VERSION}", font=("Inter", 8), bg="#0F172A", fg="#475569").pack()
        self.lbl_copyright = tk.Label(footer, font=("Inter", 7), bg="#0F172A", fg="#334155")
        self.lbl_copyright.pack()

        self.update_branding()

        # Content Area
        self.content_container = tk.Frame(self.main_container, bg="#F8FAFC")
        self.content_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Status Bar
        self.status_bar = tk.Frame(self.content_container, bg="#FFFFFF", height=30, highlightthickness=1, highlightbackground="#E2E8F0")
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        tk.Label(self.status_bar, textvariable=self.status_msg, font=("Inter", 8, "bold"), bg="#FFFFFF", fg="#64748B", padx=20).pack(side=tk.LEFT)
        tk.Label(self.status_bar, text="Ctrl+O  Open  ·  Enter  Run  ·  Esc  Stop  ·  Ctrl+L  Clear",
                 font=("Inter", 7), bg="#FFFFFF", fg="#CBD5E1", padx=20).pack(side=tk.RIGHT)

        self.render_tab()

    def update_branding(self):
        bank = self.bank_var.get()
        if bank == "IDFC First Bank":
            self.lbl_logo1.config(text="IDFC FIRST")
            self.lbl_logo2.config(fg="#2563EB")
            self.lbl_copyright.config(text="© 2026 IDFC FIRST Bank")
        elif bank == "Equitas Small Finance Bank":
            self.lbl_logo1.config(text="EQUITAS")
            self.lbl_logo2.config(fg="#D97706")
            self.lbl_copyright.config(text="© 2026 Equitas Small Finance Bank")

    def on_bank_change(self, event=None, preserve_file=None):
        set_config("bank", self.bank_var.get())
        self.update_branding()
        if preserve_file:
            self.file_var.set(preserve_file)
        else:
            self.file_var.set("")
        self.render_tab()

    def get_theme_color(self, key):
        return THEME.get(self.bank_var.get(), THEME["IDFC First Bank"])[key]

    def create_nav_btn(self, text, tag, parent):
        btn = tk.Button(parent, text=text, font=("Inter", 12, "bold"),
                        bg="#0F172A", fg="#94A3B8",
                        activebackground="#1E293B", activeforeground="#FFFFFF",
                        relief="flat", anchor="w", padx=40, pady=12,
                        cursor="hand2", borderwidth=0,
                        command=lambda: self.switch_tab(tag))
        btn.pack(fill=tk.X)
        tips = {
            "PROCESS": "Create a new audit batch from an Excel file",
            "STATS": "View generation statistics and daily activity",
            "HISTORY": "Browse and search past generation logs",
            "SETTINGS": "Manage application settings and data",
        }
        ToolTip(btn, tips.get(tag, ""))
        return btn

    def switch_tab(self, tag):
        self.active_tab = tag
        for t, b in self.nav_btns.items():
            is_active = (self.active_tab == t)
            b.config(bg="#1E293B" if is_active else "#0F172A",
                     fg="#FFFFFF" if is_active else "#94A3B8")
        self.render_tab()

    def render_tab(self):
        for w in self.content_container.winfo_children():
            if w != self.status_bar:
                w.destroy()

        self.content_scrollable = ScrollableFrame(self.content_container, bg="#F8FAFC")
        self.content_scrollable.pack(fill=tk.BOTH, expand=True)
        self.content = self.content_scrollable.scrollable_frame

        if self.active_tab == "PROCESS":
            if self.bank_var.get() == "IDFC First Bank":
                self.render_process_idfc()
            else:
                self.render_process_equitas()
        elif self.active_tab == "HISTORY":
            self.render_history()
        elif self.active_tab == "STATS":
            self.render_stats()
        elif self.active_tab == "SETTINGS":
            self.render_settings()

    # ---------------------------------------------------------
    # TAB: NEW BATCH (PROCESS) - IDFC
    # ---------------------------------------------------------
    def render_process_idfc(self):
        header = tk.Frame(self.content, bg="#F8FAFC")
        header.pack(fill=tk.X)
        tk.Label(header, text="Generate Reports", font=("Inter", 28, "bold"), bg="#F8FAFC", fg="#0F172A").pack(side=tk.LEFT)
        tk.Label(header, text="IDFC FIRST Bank", font=("Inter", 14, "bold"), bg="#DBEAFE", fg="#1E40AF", padx=10, pady=5).pack(side=tk.RIGHT)

        stats_frame = tk.Frame(self.content, bg="#F8FAFC")
        stats_frame.pack(fill=tk.X, pady=15)
        e, p = get_stats()
        self.create_stat_card(stats_frame, "Total Sessions", str(e), "#0F172A", 0)
        last_run = get_recent_history(limit=1)
        status_text = last_run[0][1] if last_run else "No activity yet"
        status_color = "#10B981" if last_run else "#94A3B8"
        self.create_stat_card(stats_frame, "Last Run", status_text[:19], status_color, 1)
        self.create_stat_card(stats_frame, "PDF Reports", str(p), self.get_theme_color("primary"), 2)

        self.panel = tk.Frame(self.content, bg="#FFFFFF", padx=30, pady=25, highlightthickness=1, highlightbackground="#E2E8F0")
        self.panel.pack(fill=tk.X)

        self.create_input(self.panel, "Source Master Excel", self.file_var, self.browse_in_idfc, "Browse...")

        self.validate_label = tk.Label(self.panel, text="", font=("Inter", 10), bg="#FFFFFF")
        self.validate_label.pack(anchor="w", pady=(0, 5))

        self.recent_frame = tk.Frame(self.panel, bg="#FFFFFF")
        self.recent_frame.pack(fill=tk.X, pady=(0, 5))
        self._refresh_recent_files()

        self.preview_frame = tk.Frame(self.panel, bg="#FFFFFF")
        self.preview_frame.pack(fill=tk.X)

        if self.file_var.get().strip() and os.path.exists(self.file_var.get().strip()):
            self._preview_file_idfc(self.file_var.get().strip())

        cfg_row = tk.Frame(self.panel, bg="#FFFFFF")
        cfg_row.pack(fill=tk.X, pady=10)

        type_box = tk.Frame(cfg_row, bg="#FFFFFF")
        type_box.pack(side=tk.LEFT)
        tk.Label(type_box, text="Audit Type:", font=("Inter", 10, "bold"), bg="#FFFFFF", fg="#475569").pack(side=tk.LEFT)
        for t in ["POA", "TAF"]:
            rb = tk.Radiobutton(type_box, text=t, variable=self.typ_var, value=t,
                           bg="#FFFFFF", font=("Inter", 11), selectcolor="#FFFFFF",
                           padx=15, command=lambda: set_config("audit_type", self.typ_var.get()))
            rb.pack(side=tk.LEFT)
            ToolTip(rb, f"Generate {t} audit worksheets")

        tk.Checkbutton(cfg_row, text="Auto-open destination folder", variable=self.auto_open,
                       bg="#FFFFFF", font=("Inter", 10), activebackground="#FFFFFF",
                       command=lambda: set_config("auto_open", str(self.auto_open.get()))).pack(side=tk.RIGHT)

        pkg_row = tk.Frame(self.panel, bg="#FFFFFF")
        pkg_row.pack(fill=tk.X, pady=(0, 5))
        tk.Label(pkg_row, text="Output Mode:", font=("Inter", 10, "bold"), bg="#FFFFFF", fg="#475569").pack(side=tk.LEFT)
        tips_map = {"FOLDER": "Save PDFs directly to a folder", "ZIP ONLY": "Compress PDFs into a ZIP archive (saves ~50% space)", "BOTH": "Keep folder + create ZIP archive"}
        for m in ["FOLDER", "ZIP ONLY", "BOTH"]:
            rb = tk.Radiobutton(pkg_row, text=m, variable=self.pkg_var, value=m,
                           bg="#FFFFFF", font=("Inter", 10), selectcolor="#FFFFFF",
                           padx=15, command=lambda: set_config("pkg_mode", self.pkg_var.get()))
            rb.pack(side=tk.LEFT)
            ToolTip(rb, tips_map[m])
        tk.Label(pkg_row, text="(ZIP ONLY saves 50% space)", font=("Inter", 8, "italic"), bg="#FFFFFF", fg="#94A3B8").pack(side=tk.LEFT, padx=10)

        self.create_input(self.panel, "Output Directory", self.folder_var, self.browse_out, "Browse...")

        btn_row = tk.Frame(self.panel, bg="#FFFFFF")
        btn_row.pack(fill=tk.X, pady=(15, 10))

        self.btn_run = tk.Button(btn_row, text="Generate Reports", font=("Inter", 14, "bold"),
                                 bg=self.get_theme_color("primary"), fg="#FFFFFF", relief="flat", padx=50, pady=12,
                                 cursor="hand2", activebackground=self.get_theme_color("primary_hover"),
                                 command=self.start_process_idfc)
        self.btn_run.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        ToolTip(self.btn_run, "Generate audit PDFs from the selected Excel file")
        self.btn_run.bind("<Control-Return>", lambda e: self.start_process_idfc())

        self.btn_cancel = tk.Button(btn_row, text="Stop", font=("Inter", 11, "bold"),
                                    bg="#DC2626", fg="#FFFFFF", relief="flat", padx=25, pady=12,
                                    cursor="hand2", activebackground="#B91C1C",
                                    state=tk.DISABLED, command=self.cancel_process)
        self.btn_cancel.pack(side=tk.RIGHT)
        ToolTip(self.btn_cancel, "Stop the current generation")

        prog_row = tk.Frame(self.panel, bg="#FFFFFF")
        prog_row.pack(fill=tk.X, pady=(0, 5))
        self.progress = ttk.Progressbar(prog_row, variable=self.progress_var, maximum=100)
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.prog_label = tk.Label(prog_row, text="0%", font=("Inter", 9, "bold"),
                                   bg="#FFFFFF", fg="#64748B", width=6, anchor="e")
        self.prog_label.pack(side=tk.RIGHT, padx=(10, 0))
        self.branch_label = tk.Label(self.panel, text="", font=("Inter", 9, "italic"),
                                     bg="#FFFFFF", fg="#64748B", anchor="w")
        self.branch_label.pack(fill=tk.X, pady=(0, 5))

        self.render_console()
 
    def browse_in_idfc(self):
        f = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx *.xls")])
        if f:
            _add_recent_file(f)
            detected = _detect_bank_from_file(f)
            if detected and detected != self.bank_var.get():
                self.bank_var.set(detected)
                self.on_bank_change(preserve_file=f)
                return
            self.file_var.set(f)
            self.status_msg.set(f"Loaded: {os.path.basename(f)}")
            valid, err = pdf_logic.validate_excel(f)
            if valid:
                self.validate_label.config(text="Valid file — all required columns found", fg="#16A34A")
            else:
                self.validate_label.config(text=err, fg="#DC2626")
            self._preview_file_idfc(f)
            self._refresh_recent_files()

    def _preview_file_idfc(self, filepath):
        valid, err = pdf_logic.validate_excel(filepath)
        if not valid:
            self.status_msg.set(err)
            self._clear_preview()
            return
        threading.Thread(target=self._do_preview_idfc, args=(filepath,), daemon=True).start()

    def _do_preview_idfc(self, filepath):
        try:
            sheet, headers, rows = pdf_logic.read_excel(filepath, log_callback=lambda x: None)
            groups = pdf_logic.group_by_branch(rows)
            self.root.after(0, lambda: self._show_preview(sheet, len(rows), len(groups), "branches"))
        except Exception as e:
            self.root.after(0, lambda: self.status_msg.set(f"Preview: {e}"))
            self.root.after(0, self._clear_preview)


    # ---------------------------------------------------------
    # TAB: NEW BATCH (PROCESS) - EQUITAS
    # ---------------------------------------------------------
    def render_process_equitas(self):
        header = tk.Frame(self.content, bg="#F8FAFC")
        header.pack(fill=tk.X)
        tk.Label(header, text="Generate Reports", font=("Inter", 28, "bold"), bg="#F8FAFC", fg="#0F172A").pack(side=tk.LEFT)
        tk.Label(header, text="Equitas Small Finance Bank", font=("Inter", 14, "bold"), bg="#FEF3C7", fg="#92400E", padx=10, pady=5).pack(side=tk.RIGHT)

        # Stage Selector
        stage_frame = tk.Frame(self.content, bg="#F8FAFC")
        stage_frame.pack(fill=tk.X, pady=(15, 0))

        stage_box = tk.Frame(stage_frame, bg="#FFFFFF", highlightthickness=1, highlightbackground="#E2E8F0", padx=5, pady=5)
        stage_box.pack(side=tk.LEFT)

        def switch_stage():
            current_path = self.file_var.get().strip()
            self.render_tab()
            if current_path and os.path.exists(current_path):
                self.file_var.set(current_path)
                self.status_msg.set(f"Loaded: {os.path.basename(current_path)}")
                stage = self.equitas_stage_var.get()
                if stage == "STAGE 1":
                    valid, info = equitas_logic.validate_equitas_stage1_file(current_path)
                    if valid:
                        self.validate_label.config(text="Valid file — sheet pairs found", fg="#16A34A")
                        self._preview_file_equitas_s1(current_path)
                    else:
                        self.validate_label.config(text=info, fg="#DC2626")
                        self._clear_preview()
                else:
                    valid, info = equitas_logic.validate_equitas_stage2_file(current_path)
                    if valid:
                        self.validate_label.config(text="Valid file — required columns found", fg="#16A34A")
                        self._preview_file_equitas_s2(current_path)
                    else:
                        self.validate_label.config(text=info, fg="#DC2626")
                        self._clear_preview()

        for s in ["STAGE 1", "STAGE 2"]:
            rb = tk.Radiobutton(stage_box, text=s, variable=self.equitas_stage_var, value=s,
                           bg="#FFFFFF", font=("Inter", 11, "bold" if self.equitas_stage_var.get() == s else "normal"),
                           selectcolor="#FFFFFF", activebackground="#FFFFFF", indicatoron=0,
                           fg=self.get_theme_color("primary") if self.equitas_stage_var.get() == s else "#64748B",
                           relief="flat", padx=20, pady=5, command=switch_stage)
            rb.pack(side=tk.LEFT)
            stage_tips = {"STAGE 1": "Generate branch-level PDFs and Excel templates from master data",
                          "STAGE 2": "Consolidate audited Stage 1 Excel into a final account-level report"}
            ToolTip(rb, stage_tips.get(s, ""))

        # Panel
        self.panel = tk.Frame(self.content, bg="#FFFFFF", padx=30, pady=25, highlightthickness=1, highlightbackground="#E2E8F0")
        self.panel.pack(fill=tk.X, pady=(10, 0))

        stage = self.equitas_stage_var.get()

        if stage == "STAGE 1":
            tk.Label(self.panel, text="Stage 1: Generate Branch Audits & Excels", font=("Inter", 12, "bold"), bg="#FFFFFF", fg="#0F172A").pack(anchor="w", pady=(0, 15))
            self.create_input(self.panel, "Source Excel (Normal + JSR sheets)", self.file_var, self.browse_in_equitas, "Browse...")

            # --- Format & Packaging options ---
            eq_cfg_frame = tk.Frame(self.panel, bg="#FFFFFF")
            eq_cfg_frame.pack(fill=tk.X, pady=(0, 10))

            format_frame = tk.Frame(eq_cfg_frame, bg="#FFFFFF")
            format_frame.pack(side=tk.LEFT)
            tk.Label(format_frame, text="Output Format:", font=("Inter", 10, "bold"), bg="#FFFFFF", fg="#475569").pack(side=tk.LEFT)
            fmt_tips = {"PDF ONLY": "Generate only PDF audit worksheets", "EXCEL ONLY": "Generate only Excel templates with formulas", "BOTH": "Generate both PDF and Excel outputs"}
            for m in ["PDF ONLY", "EXCEL ONLY", "BOTH"]:
                rb = tk.Radiobutton(format_frame, text=m, variable=self.equitas_format_var, value=m,
                               bg="#FFFFFF", font=("Inter", 10), selectcolor="#FFFFFF",
                               padx=10, command=lambda: set_config("equitas_format", self.equitas_format_var.get()))
                rb.pack(side=tk.LEFT)
                ToolTip(rb, fmt_tips[m])

            pack_frame = tk.Frame(eq_cfg_frame, bg="#FFFFFF")
            pack_frame.pack(side=tk.RIGHT)
            tk.Label(pack_frame, text="Packaging:", font=("Inter", 10, "bold"), bg="#FFFFFF", fg="#475569").pack(side=tk.LEFT, padx=(10, 5))
            self.equitas_pack_combo = ttk.Combobox(
                pack_frame, textvariable=self.equitas_pack_var,
                values=[
                    "FOLDER",
                    "ZIP OF PDF",
                    "ZIP OF EXCEL",
                    "ZIP OF BOTH",
                    "BOTH (FOLDER + ZIP OF PDF)",
                    "BOTH (FOLDER + ZIP OF EXCEL)",
                    "BOTH (FOLDER + ZIP OF BOTH)"
                ],
                state="readonly", font=("Inter", 10), width=28
            )
            self.equitas_pack_combo.pack(side=tk.LEFT)
            self.equitas_pack_combo.bind("<<ComboboxSelected>>", lambda e: set_config("equitas_pack", self.equitas_pack_var.get()))
            ToolTip(self.equitas_pack_combo, "Choose how to package the generated output files")
        else:
            tk.Label(self.panel, text="Stage 2: Consolidate Audited Excels", font=("Inter", 12, "bold"), bg="#FFFFFF", fg="#0F172A").pack(anchor="w", pady=(0, 15))
            self.create_input(self.panel, "Audited Stage 1 Excel", self.file_var, self.browse_in_equitas, "Browse...")

        self.validate_label = tk.Label(self.panel, text="", font=("Inter", 10), bg="#FFFFFF")
        self.validate_label.pack(anchor="w", pady=(0, 5))

        self.recent_frame = tk.Frame(self.panel, bg="#FFFFFF")
        self.recent_frame.pack(fill=tk.X, pady=(0, 5))
        self._refresh_recent_files()

        self.preview_frame = tk.Frame(self.panel, bg="#FFFFFF")
        self.preview_frame.pack(fill=tk.X)

        if self.file_var.get().strip() and os.path.exists(self.file_var.get().strip()):
            if stage == "STAGE 1":
                self._preview_file_equitas_s1(self.file_var.get().strip())
            else:
                self._preview_file_equitas_s2(self.file_var.get().strip())

        tk.Frame(self.panel, bg="#E2E8F0", height=1).pack(fill=tk.X, pady=15)

        self.create_input(self.panel, "Output Directory", self.folder_var, self.browse_out, "Browse...")

        cfg_row = tk.Frame(self.panel, bg="#FFFFFF")
        cfg_row.pack(fill=tk.X, pady=(0, 5))
        tk.Checkbutton(cfg_row, text="Auto-open destination folder", variable=self.auto_open,
                       bg="#FFFFFF", font=("Inter", 10), activebackground="#FFFFFF",
                       command=lambda: set_config("auto_open", str(self.auto_open.get()))).pack(side=tk.RIGHT)

        btn_row = tk.Frame(self.panel, bg="#FFFFFF")
        btn_row.pack(fill=tk.X, pady=(15, 10))

        btn_text = "Generate (Stage 1)" if stage == "STAGE 1" else "Consolidate (Stage 2)"

        self.btn_run = tk.Button(btn_row, text=btn_text, font=("Inter", 14, "bold"),
                                 bg=self.get_theme_color("primary"), fg="#FFFFFF", relief="flat", padx=50, pady=12,
                                 cursor="hand2", activebackground=self.get_theme_color("primary_hover"),
                                 command=self.start_process_equitas)
        self.btn_run.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        ToolTip(self.btn_run, f"Run Equitas {stage} processing")

        self.btn_cancel = tk.Button(btn_row, text="Stop", font=("Inter", 11, "bold"),
                                    bg="#DC2626", fg="#FFFFFF", relief="flat", padx=25, pady=12,
                                    cursor="hand2", activebackground="#B91C1C",
                                    state=tk.DISABLED, command=self.cancel_process)
        self.btn_cancel.pack(side=tk.RIGHT)
        ToolTip(self.btn_cancel, "Stop the current generation")

        prog_row = tk.Frame(self.panel, bg="#FFFFFF")
        prog_row.pack(fill=tk.X, pady=(0, 5))
        self.progress = ttk.Progressbar(prog_row, variable=self.progress_var, maximum=100)
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.prog_label = tk.Label(prog_row, text="0%", font=("Inter", 9, "bold"),
                                   bg="#FFFFFF", fg="#64748B", width=6, anchor="e")
        self.prog_label.pack(side=tk.RIGHT, padx=(10, 0))
        self.branch_label = tk.Label(self.panel, text="", font=("Inter", 9, "italic"),
                                     bg="#FFFFFF", fg="#64748B", anchor="w")
        self.branch_label.pack(fill=tk.X, pady=(0, 5))

        self.render_console()

    def browse_in_equitas(self):
        f = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx *.xls")])
        if not f:
            return
        _add_recent_file(f)
        detected = _detect_bank_from_file(f)
        if detected and detected != self.bank_var.get():
            self.bank_var.set(detected)
            self.on_bank_change(preserve_file=f)
            return

        # Auto-detect stage
        s1_valid, s1_info = equitas_logic.validate_equitas_stage1_file(f)
        if s1_valid:
            new_stage = "STAGE 1"
        else:
            s2_valid, s2_info = equitas_logic.validate_equitas_stage2_file(f)
            new_stage = "STAGE 2" if s2_valid else self.equitas_stage_var.get()

        self.equitas_stage_var.set(new_stage)
        self.file_var.set(f)
        self.status_msg.set(f"Loaded: {os.path.basename(f)} (detected {new_stage})")
        self.render_tab()
        # render_tab triggers preview automatically for the loaded file

    def browse_in_equitas_s1(self):
        f = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx *.xls")])
        if f:
            _add_recent_file(f)
            detected = _detect_bank_from_file(f)
            if detected and detected != self.bank_var.get():
                self.bank_var.set(detected)
                self.on_bank_change(preserve_file=f)
                return
            self.file_var.set(f)
            self.status_msg.set(f"Loaded: {os.path.basename(f)}")
            valid, info = equitas_logic.validate_equitas_stage1_file(f)
            if valid:
                self.validate_label.config(text="Valid file — sheet pairs found", fg="#16A34A")
            else:
                self.validate_label.config(text=info, fg="#DC2626")
            self._preview_file_equitas_s1(f)
            self._refresh_recent_files()

    def browse_in_equitas_s2(self):
        f = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx *.xls")])
        if f:
            _add_recent_file(f)
            detected = _detect_bank_from_file(f)
            if detected and detected != self.bank_var.get():
                self.bank_var.set(detected)
                self.on_bank_change(preserve_file=f)
                return
            self.file_var.set(f)
            self.status_msg.set(f"Loaded: {os.path.basename(f)}")
            valid, info = equitas_logic.validate_equitas_stage2_file(f)
            if valid:
                self.validate_label.config(text="Valid file — required columns found", fg="#16A34A")
            else:
                self.validate_label.config(text=info, fg="#DC2626")
            self._preview_file_equitas_s2(f)
            self._refresh_recent_files()

    def _preview_file_equitas_s1(self, filepath):
        threading.Thread(target=self._do_preview_equitas_s1, args=(filepath,), daemon=True).start()

    def _do_preview_equitas_s1(self, filepath):
        valid, info_or_err = equitas_logic.validate_equitas_stage1_file(filepath)
        if not valid:
            self.root.after(0, lambda: self.status_msg.set(info_or_err))
            self.root.after(0, self._clear_preview)
        else:
            pairs = info_or_err["sheet_pairs"]
            rows = info_or_err["sample_rows"]
            names = ", ".join(info_or_err["pair_names"])
            self.root.after(0, lambda: self._show_preview(names, rows, pairs, "sheet pairs"))

    def _preview_file_equitas_s2(self, filepath):
        threading.Thread(target=self._do_preview_equitas_s2, args=(filepath,), daemon=True).start()

    def _do_preview_equitas_s2(self, filepath):
        valid, info_or_err = equitas_logic.validate_equitas_stage2_file(filepath)
        if not valid:
            self.root.after(0, lambda: self.status_msg.set(info_or_err))
            self.root.after(0, self._clear_preview)
        else:
            rows = info_or_err["row_count"]
            accs = info_or_err["account_count"]
            self.root.after(0, lambda: self._show_preview("Audit", rows, accs, "accounts"))

    # ---------------------------------------------------------
    # SHARED PREVIEW / CONSOLE
    # ---------------------------------------------------------
    def _show_preview(self, title_info, row_count, count, count_label):
        self._clear_preview()
        info = tk.Frame(self.preview_frame, bg="#F0FDF4", padx=15, pady=8,
                        highlightthickness=1, highlightbackground="#86EFAC")
        info.pack(fill=tk.X, pady=(5, 0))
        tk.Label(info, text="File loaded:", font=("Inter", 10, "bold"), bg="#F0FDF4", fg="#16A34A").pack(side=tk.LEFT)
        tk.Label(info, text=f" {title_info}   |   Rows: {row_count:,}   |   {count_label.title()}: {count:,}",
                 font=("Inter", 10), bg="#F0FDF4", fg="#15803D").pack(side=tk.LEFT, padx=(5, 0))
        self.status_msg.set(f"Ready — {row_count:,} rows, {count:,} {count_label}")

    def _clear_preview(self):
        if hasattr(self, 'preview_frame'):
            for w in self.preview_frame.winfo_children():
                w.destroy()
        if hasattr(self, 'validate_label'):
            self.validate_label.config(text="")

    def _refresh_recent_files(self):
        if not hasattr(self, 'recent_frame'):
            return
        for w in self.recent_frame.winfo_children():
            w.destroy()
        files = _get_recent_files()
        if files:
            tk.Label(self.recent_frame, text="Recent:", font=("Inter", 8, "bold"),
                     bg="#FFFFFF", fg="#94A3B8").pack(side=tk.LEFT, padx=(0, 8))
            for f in files[:5]:
                short = os.path.basename(f)
                btn = tk.Button(self.recent_frame, text=short, font=("Inter", 8),
                                bg="#F1F5F9", fg="#2563EB", relief="flat",
                                padx=8, cursor="hand2",
                                command=lambda path=f: self._load_recent_file(path))
                btn.pack(side=tk.LEFT, padx=2)
                ToolTip(btn, f"Load: {f}")

    def _load_recent_file(self, f):
        self.file_var.set(f)
        self.status_msg.set(f"Loaded: {os.path.basename(f)}")
        self._clear_preview()
        bank = self.bank_var.get()
        if bank == "IDFC First Bank":
            valid, err = pdf_logic.validate_excel(f)
            self.validate_label.config(text="Valid file — all required columns found" if valid else err,
                                       fg="#16A34A" if valid else "#DC2626")
            self._preview_file_idfc(f)
        else:
            stage = self.equitas_stage_var.get()
            if stage == "STAGE 1":
                valid, info = equitas_logic.validate_equitas_stage1_file(f)
                self.validate_label.config(text="Valid file — sheet pairs found" if valid else info,
                                           fg="#16A34A" if valid else "#DC2626")
                self._preview_file_equitas_s1(f)
            else:
                valid, info = equitas_logic.validate_equitas_stage2_file(f)
                self.validate_label.config(text="Valid file — required columns found" if valid else info,
                                           fg="#16A34A" if valid else "#DC2626")
                self._preview_file_equitas_s2(f)

    def render_console(self):
        con_hdr = tk.Frame(self.content, bg="#F8FAFC")
        con_hdr.pack(fill=tk.X, pady=(15, 5))
        tk.Label(con_hdr, text="Console Logs", font=("Inter", 9, "bold"), bg="#F8FAFC", fg="#94A3B8").pack(side=tk.LEFT)
        copy_btn = tk.Button(con_hdr, text="Copy", font=("Inter", 8, "bold"), bg="#F1F5F9", relief="flat", padx=10, command=self.copy_logs)
        copy_btn.pack(side=tk.RIGHT)
        ToolTip(copy_btn, "Copy all console logs to clipboard")

        self.log_area = scrolledtext.ScrolledText(self.content, height=8, bg="#1E293B", fg="#10B981",
                                                  borderwidth=0, font=("Menlo", 10), padx=20, pady=20)
        self.log_area.pack(fill=tk.BOTH, expand=True)

    def browse_out(self):
        f = filedialog.askdirectory()
        if f:
            self.folder_var.set(f)
            set_config("out_path", f)

    # ---------------------------------------------------------
    # TAB: ANALYTICS, HISTORY, SETTINGS (SHARED)
    # ---------------------------------------------------------
    def render_stats(self):
        header = tk.Frame(self.content, bg="#F8FAFC")
        header.pack(fill=tk.X, pady=(0, 40))
        tk.Label(header, text="Insight Analytics", font=("Inter", 28, "bold"), bg="#F8FAFC", fg="#0F172A").pack(side=tk.LEFT)
        refresh_btn = tk.Button(header, text="Refresh", font=("Inter", 10), bg="#F1F5F9", relief="flat", command=lambda: self.render_tab())
        refresh_btn.pack(side=tk.RIGHT)
        ToolTip(refresh_btn, "Refresh analytics data")

        types, trend = get_analytics()
        grid = tk.Frame(self.content, bg="#F8FAFC")
        grid.pack(fill=tk.BOTH, expand=True)

        dist_card = tk.Frame(grid, bg="#FFFFFF", padx=40, pady=40, highlightthickness=1, highlightbackground="#E2E8F0")
        dist_card.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        tk.Label(dist_card, text="Audit Type Distribution", font=("Inter", 11, "bold"), bg="#FFFFFF", fg="#64748B").pack(anchor="w", pady=(0, 30))

        total = sum(types.values()) if types else 0
        for t in ["POA", "TAF", "Equitas-S1", "Equitas-S2"]:
            count = types.get(t, 0)
            if count == 0 and total > 0: continue
            pct = (count / total * 100) if total > 0 else 0
            row = tk.Frame(dist_card, bg="#FFFFFF", pady=10)
            row.pack(fill=tk.X)
            tk.Label(row, text=t, font=("Inter", 12), bg="#FFFFFF").pack(side=tk.LEFT)
            tk.Label(row, text=f"{count}", font=("Inter", 12, "bold"), bg="#FFFFFF", fg=self.get_theme_color("primary")).pack(side=tk.RIGHT)
            p = ttk.Progressbar(dist_card, value=pct)
            p.pack(fill=tk.X, pady=(0, 20))

        trend_card = tk.Frame(grid, bg="#FFFFFF", padx=40, pady=40, highlightthickness=1, highlightbackground="#E2E8F0")
        trend_card.grid(row=0, column=1, sticky="nsew")
        tk.Label(trend_card, text="Daily Activity (7 Days)", font=("Inter", 11, "bold"), bg="#FFFFFF", fg="#64748B").pack(anchor="w", pady=(0, 30))
        if trend:
            for d, c in trend:
                r = tk.Frame(trend_card, bg="#FFFFFF", pady=8)
                r.pack(fill=tk.X)
                tk.Label(r, text=d, font=("Inter", 11), bg="#FFFFFF").pack(side=tk.LEFT)
                tk.Label(r, text=f"{c} Batches", font=("Inter", 11, "bold"), bg="#FFFFFF", fg="#059669").pack(side=tk.RIGHT)
        else:
            tk.Label(trend_card, text="No activity yet", font=("Inter", 11), bg="#FFFFFF", fg="#94A3B8").pack(anchor="w")

        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)

    def render_history(self):
        header = tk.Frame(self.content, bg="#F8FAFC")
        header.pack(fill=tk.X, pady=(0, 30))
        tk.Label(header, text="History", font=("Inter", 28, "bold"), bg="#F8FAFC", fg="#0F172A").pack(side=tk.LEFT)

        search_f = tk.Frame(self.content, bg="#F8FAFC")
        search_f.pack(fill=tk.X, pady=(0, 25))
        search_entry = tk.Entry(search_f, textvariable=self.search_var, font=("Inter", 12),
                                bg="#FFFFFF", highlightthickness=1, highlightbackground="#E2E8F0", relief="flat")
        search_entry.pack(fill=tk.X, ipady=12)
        if not self.search_var.get():
            search_entry.insert(0, "")
            search_entry.config(fg="#94A3B8")

        table_container = tk.Frame(self.content, bg="#FFFFFF", highlightthickness=1, highlightbackground="#E2E8F0")
        table_container.pack(fill=tk.BOTH, expand=True)

        cols = ("Time", "Filename", "Items", "Type")
        self.tree = ttk.Treeview(table_container, columns=cols, show="headings", height=15)
        for c in cols:
            self.tree.heading(c, text=c.upper(), anchor="center")
        self.tree.column("Time", width=200, anchor="center")
        self.tree.column("Filename", width=450, anchor="w")
        self.tree.column("Items", width=120, anchor="center")
        self.tree.column("Type", width=120, anchor="center")

        sb = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.refresh_history()

        btn_bar = tk.Frame(self.content, bg="#F8FAFC", pady=30)
        btn_bar.pack(fill=tk.X)
        open_btn = tk.Button(btn_bar, text="Open Folder", bg=self.get_theme_color("primary"), fg="#FFFFFF", font=("Inter", 11, "bold"),
                  relief="flat", padx=30, pady=12, command=self.open_sel)
        open_btn.pack(side=tk.LEFT, padx=(0, 10))
        ToolTip(open_btn, "Open output folder of selected entry")
        re_run_btn = tk.Button(btn_bar, text="Re-run", bg="#2563EB", fg="#FFFFFF", font=("Inter", 11, "bold"),
                  relief="flat", padx=30, pady=12, command=self.re_run_history)
        re_run_btn.pack(side=tk.LEFT)
        ToolTip(re_run_btn, "Re-run generation with the same file and settings")
        export_btn = tk.Button(btn_bar, text="Export to Excel", bg="#059669", fg="#FFFFFF", font=("Inter", 11, "bold"),
                  relief="flat", padx=30, pady=12, command=self.export_history)
        export_btn.pack(side=tk.RIGHT)
        ToolTip(export_btn, "Export history to Excel spreadsheet")

    def render_settings(self):
        tk.Label(self.content, text="Settings", font=("Inter", 28, "bold"), bg="#F8FAFC", fg="#0F172A").pack(anchor="w", pady=(0, 40))

        # --- Naming Configuration ---
        naming_card = tk.Frame(self.content, bg="#FFFFFF", padx=50, pady=40, highlightthickness=1, highlightbackground="#E2E8F0")
        naming_card.pack(fill=tk.X, pady=(0, 20))
        tk.Label(naming_card, text="Output Naming", font=("Inter", 11, "bold"), bg="#FFFFFF", fg="#64748B").pack(anchor="w", pady=(0, 15))
        tk.Label(naming_card, text="Pattern:  {branch} = branch name,  {type} = audit type", font=("Inter", 9), bg="#FFFFFF", fg="#94A3B8").pack(anchor="w")
        naming_row = tk.Frame(naming_card, bg="#FFFFFF")
        naming_row.pack(fill=tk.X, pady=(10, 5))
        self.naming_var = tk.StringVar(value=get_config("naming_pattern", "{branch}_{type}"))
        tk.Entry(naming_row, textvariable=self.naming_var, font=("Inter", 12), bg="#F8FAFC", relief="flat",
                 highlightthickness=1, highlightbackground="#E2E8F0").pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0, 15))
        def save_naming():
            set_config("naming_pattern", self.naming_var.get())
            self.status_msg.set("Naming pattern saved!")
            self.root.after(2000, lambda: self.status_msg.set("Ready"))
        save_btn = tk.Button(naming_row, text="Save", font=("Inter", 10, "bold"), bg=self.get_theme_color("primary"),
                             fg="#FFFFFF", relief="flat", padx=25, pady=8, command=save_naming)
        save_btn.pack(side=tk.LEFT)
        ToolTip(save_btn, "Save custom output file naming pattern")
        preview_naming = f"e.g. {self.naming_var.get().replace('{branch}', 'BRANCH_A').replace('{type}', 'POA')}.pdf"
        tk.Label(naming_card, text=preview_naming, font=("Inter", 9, "italic"), bg="#FFFFFF", fg="#64748B").pack(anchor="w", pady=(5, 0))

        # --- Updates ---
        update_card = tk.Frame(self.content, bg="#FFFFFF", padx=50, pady=40, highlightthickness=1, highlightbackground="#E2E8F0")
        update_card.pack(fill=tk.X, pady=(0, 20))
        tk.Label(update_card, text="Updates", font=("Inter", 11, "bold"), bg="#FFFFFF", fg="#64748B").pack(anchor="w", pady=(0, 15))
        ver_row = tk.Frame(update_card, bg="#FFFFFF")
        ver_row.pack(fill=tk.X, pady=5)
        tk.Label(ver_row, text=f"Current version: v{VERSION}", font=("Inter", 10), bg="#FFFFFF", fg="#475569").pack(side=tk.LEFT)
        self.update_status = tk.Label(ver_row, text="", font=("Inter", 10), bg="#FFFFFF")
        self.update_status.pack(side=tk.LEFT, padx=(15, 0))
        btn_row = tk.Frame(update_card, bg="#FFFFFF")
        btn_row.pack(fill=tk.X, pady=10)
        self.update_btn = tk.Button(btn_row, text="Check for Updates", font=("Inter", 10, "bold"),
                                     bg=self.get_theme_color("primary"), fg="#FFFFFF", relief="flat",
                                     padx=20, pady=8, command=self._check_updates_manual)
        self.update_btn.pack(side=tk.LEFT)
        ToolTip(self.update_btn, "Check GitHub for a newer version")
        self.update_progress = ttk.Progressbar(btn_row, length=200, mode="determinate")
        self.update_progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(15, 0))

        # --- Default Preferences ---
        prefs_card = tk.Frame(self.content, bg="#FFFFFF", padx=50, pady=40, highlightthickness=1, highlightbackground="#E2E8F0")
        prefs_card.pack(fill=tk.X, pady=(0, 20))
        tk.Label(prefs_card, text="Default Preferences", font=("Inter", 11, "bold"), bg="#FFFFFF", fg="#64748B").pack(anchor="w", pady=(0, 15))

        # Auto-open default
        auto_row = tk.Frame(prefs_card, bg="#FFFFFF")
        auto_row.pack(fill=tk.X, pady=8)
        self.auto_open_saved = tk.BooleanVar(value=get_config("auto_open", "True") == "True")
        tk.Checkbutton(auto_row, text="Auto-open destination folder after generation", variable=self.auto_open_saved,
                       bg="#FFFFFF", font=("Inter", 10), activebackground="#FFFFFF",
                       command=lambda: set_config("auto_open", str(self.auto_open_saved.get()))).pack(side=tk.LEFT)
        ToolTip(auto_row, "When checked, the output folder opens automatically after each generation")

        # Recent files control
        recent_row = tk.Frame(prefs_card, bg="#FFFFFF")
        recent_row.pack(fill=tk.X, pady=8)
        tk.Label(recent_row, text=f"Recent files: {len(_get_recent_files())} saved", font=("Inter", 10),
                 bg="#FFFFFF", fg="#475569").pack(side=tk.LEFT, padx=(0, 15))
        def clear_recent():
            for i in range(MAX_RECENT_FILES):
                set_config(f"recent_file_{i}", "")
            self.status_msg.set("Recent files cleared")
            self.render_tab()
        tk.Button(recent_row, text="Clear Recent Files", font=("Inter", 9, "bold"), bg="#F1F5F9", fg="#E11D48",
                  relief="flat", padx=16, pady=6, command=clear_recent).pack(side=tk.LEFT)

        # --- Database Management ---
        card = tk.Frame(self.content, bg="#FFFFFF", padx=50, pady=40, highlightthickness=1, highlightbackground="#E2E8F0")
        card.pack(fill=tk.X)
        tk.Label(card, text="Database Management", font=("Inter", 11, "bold"), bg="#FFFFFF", fg="#64748B").pack(anchor="w", pady=(0, 20))
        tk.Label(card, text=f"DB: {DB_PATH}", font=("Inter", 10), bg="#FFFFFF", fg="#94A3B8").pack(anchor="w", pady=(5, 5))
        tk.Label(card, text=f"Log: {LOG_FILE}", font=("Inter", 10), bg="#FFFFFF", fg="#94A3B8").pack(anchor="w", pady=(0, 30))
        clear_btn = tk.Button(card, text="Clear History", font=("Inter", 10, "bold"), bg="#F1F5F9", fg="#E11D48",
                  relief="flat", padx=24, pady=10, command=self.clear_history)
        clear_btn.pack(anchor="w")
        ToolTip(clear_btn, "Delete all history records")

    # ---------------------------------------------------------
    # AUTO-UPDATER
    # ---------------------------------------------------------
    def _check_updates_background(self):
        """Silent background check on startup — downloads and shows notification."""
        threading.Thread(target=self._do_background_update, daemon=True).start()

    def _do_background_update(self):
        try:
            latest_tag, download_url, notes, binary_url = _check_latest_release()
            latest_ver = _parse_version(latest_tag)
            current_ver = _parse_version(VERSION)
            if latest_ver <= current_ver:
                return
            if getattr(sys, "frozen", False):
                if not binary_url:
                    print(f"[background] No binary asset for {latest_tag} yet; will retry in 5 min.")
                    self.root.after(300000, self._check_updates_background)
                    return
                url = binary_url
            else:
                url = download_url
            tmp = _tempfile.mkdtemp(prefix="audit_update_")
            zip_path = os.path.join(tmp, f"update_{latest_tag}.zip")
            _download_update(url, zip_path)
            install_dir = _get_install_dir()
            if getattr(sys, "frozen", False):
                result = _install_binary_update(zip_path, install_dir, print)
                if result and sys.platform == "win32":
                    # Batch script is staged — show notification to user
                    self._pending_update_bat = result
                    self.root.after(0, lambda: self._show_update_banner(latest_tag))
                    return
            else:
                _install_update(zip_path, install_dir, print)
            _shutil.rmtree(tmp, ignore_errors=True)
            # Non-Windows or source mode: restart directly
            self.root.after(0, lambda: self._show_update_banner(latest_tag))
        except Exception as e:
            print(f"[background] Update failed: {e}")

    def _show_update_banner(self, tag):
        """Show a non-intrusive notification banner that an update is ready."""
        try:
            # Create a banner at the top of the content area
            self._update_banner = tk.Frame(self.content_container, bg="#059669", height=40)
            self._update_banner.pack(side=tk.TOP, fill=tk.X, before=self.content_scrollable)
            self._update_banner.pack_propagate(False)

            inner = tk.Frame(self._update_banner, bg="#059669")
            inner.pack(expand=True)

            tk.Label(inner, text=f"✓ Update {tag} downloaded — ",
                     font=("Inter", 10, "bold"), bg="#059669", fg="#FFFFFF").pack(side=tk.LEFT)

            restart_btn = tk.Button(inner, text="Restart Now", font=("Inter", 10, "bold"),
                                    bg="#FFFFFF", fg="#059669", relief="flat", padx=12, pady=2,
                                    cursor="hand2", command=self._exit_for_update)
            restart_btn.pack(side=tk.LEFT, padx=(0, 10))

            dismiss_btn = tk.Button(inner, text="Later", font=("Inter", 9),
                                    bg="#059669", fg="#D1FAE5", relief="flat", padx=8, pady=2,
                                    cursor="hand2", activebackground="#047857", activeforeground="#FFFFFF",
                                    command=lambda: self._update_banner.pack_forget())
            dismiss_btn.pack(side=tk.LEFT)

            self.status_msg.set(f"Update {tag} ready — restart to apply")
        except (tk.TclError, AttributeError):
            pass

    def _exit_for_update(self):
        """Cleanly exit the application so the update batch script can take over.

        Uses sys.exit(0) so PyInstaller's atexit handlers run and release
        the _MEI temp directory. On Windows frozen builds, the batch script
        (launched by _install_binary_update) will then copy the new exe,
        clean up, and relaunch the app.
        """
        try:
            self.root.update_idletasks()
            self.root.destroy()
        except (tk.TclError, AttributeError):
            pass
        # sys.exit runs atexit handlers → PyInstaller cleans up _MEI
        sys.exit(0)

    def _check_updates_manual(self):
        """Manual check triggered by user clicking the button."""
        self.update_btn.config(state=tk.DISABLED, text="Checking...")
        self.update_status.config(text="", fg="#475569")
        threading.Thread(target=self._do_check_updates, args=(False,), daemon=True).start()

    def _do_check_updates(self, background=False):
        try:
            latest_tag, download_url, notes, binary_url = _check_latest_release()
            latest_ver = _parse_version(latest_tag)
            current_ver = _parse_version(VERSION)

            url = binary_url if (getattr(sys, "frozen", False) and binary_url) else download_url

            if latest_ver <= current_ver:
                if not background:
                    self.root.after(0, lambda: self.update_status.config(text="Up to date", fg="#10B981"))
                    self.root.after(0, lambda: self.update_btn.config(state=tk.NORMAL, text="Check for Updates"))
                return

            if background:
                self.root.after(0, lambda: self._start_update(latest_tag, url))
            else:
                self.root.after(0, lambda: self._show_update_dialog(latest_tag, url, notes))

        except Exception as e:
            if not background:
                self.root.after(0, lambda: self.update_status.config(text=f"Failed: {e}", fg="#EF4444"))
                self.root.after(0, lambda: self.update_btn.config(state=tk.NORMAL, text="Check for Updates"))

    def _show_update_dialog(self, tag, url, notes):
        """Show the update-available dialog."""
        short_notes = notes[:500] + "..." if notes and len(notes) > 500 else (notes or "")
        msg = f"Version {tag} is available (you have v{VERSION}).\n\nWhat's new:\n{short_notes}\n\nDownload and install now?"
        if not messagebox.askyesno("Update Available", msg, icon=messagebox.INFO):
            self.update_status.config(text=f"v{tag} available", fg="#D97706")
            self.update_btn.config(state=tk.NORMAL, text="Check for Updates")
            return
        self._start_update(tag, url)

    def _start_update(self, tag, url):
        """Begin downloading and installing the update."""
        self.update_btn.config(state=tk.DISABLED, text="Downloading...")
        self.update_status.config(text="Downloading update...", fg="#2563EB")
        threading.Thread(target=self._do_download_install, args=(tag, url), daemon=True).start()

    def _do_download_install(self, tag, url):
        try:
            tmp = _tempfile.mkdtemp(prefix="audit_update_")
            zip_path = os.path.join(tmp, f"update_{tag}.zip")

            def prog(val):
                self.root.after(0, lambda: self.update_progress.configure(value=val))
                if val >= 100:
                    self.root.after(0, lambda: self.update_status.config(text="Installing...", fg="#2563EB"))

            _download_update(url, zip_path, prog)

            install_dir = _get_install_dir()

            if getattr(sys, "frozen", False):
                result = _install_binary_update(zip_path, install_dir, self.log)
                if result and sys.platform == "win32":
                    # Windows frozen: batch script is now running in background
                    # waiting for us to exit. Don't call _restart_app — the batch
                    # script handles copy + restart. Just exit cleanly.
                    self._pending_update_bat = result
                    _shutil.rmtree(tmp, ignore_errors=True)
                    self.root.after(0, lambda: self.update_status.config(
                        text="Update ready! Restarting...", fg="#10B981"))
                    self.root.after(0, lambda: self.update_progress.configure(value=0))
                    self.root.after(1500, self._exit_for_update)
                    return
            else:
                _install_update(zip_path, install_dir, self.log)

            _shutil.rmtree(tmp, ignore_errors=True)

            self.root.after(0, lambda: self.update_status.config(text="Update installed! Restarting...", fg="#10B981"))
            self.root.after(0, lambda: self.update_progress.configure(value=0))
            self.root.after(1500, _restart_app)

        except Exception as e:
            self.root.after(0, lambda: self.update_status.config(text=f"Update failed: {e}", fg="#EF4444"))
            self.root.after(0, lambda: self.update_btn.config(state=tk.NORMAL, text="Check for Updates"))
            self.log(f"Update failed: {e}", "ERROR")

    # ---------------------------------------------------------
    # HELPERS
    # ---------------------------------------------------------
    def clear_history(self):
        if messagebox.askyesno("Confirm", "Delete all records?"):
            conn = _connect_db()
            conn.execute("DELETE FROM history")
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "History cleared.")
            self.render_tab()

    def create_stat_card(self, parent, title, val, color, col):
        card = tk.Frame(parent, bg="#FFFFFF", padx=25, pady=20, highlightthickness=1, highlightbackground="#E2E8F0")
        card.grid(row=0, column=col, sticky="nsew", padx=10)
        parent.grid_columnconfigure(col, weight=1)
        tk.Label(card, text=title.upper(), font=("Inter", 9, "bold"), bg="#FFFFFF", fg="#94A3B8").pack(anchor="w")
        tk.Label(card, text=val, font=("Inter", 24, "bold"), bg="#FFFFFF", fg=color).pack(anchor="w", pady=(15, 0))

    def create_input(self, parent, label, var, cmd, btn_txt):
        if label:
            tk.Label(parent, text=label, font=("Inter", 11, "bold"), bg="#FFFFFF", fg="#1E293B").pack(anchor="w")
        row = tk.Frame(parent, bg="#FFFFFF")
        row.pack(fill=tk.X, pady=(8, 8))
        entry = tk.Entry(row, textvariable=var, font=("Inter", 12), bg="#F8FAFC", relief="flat",
                 highlightthickness=1, highlightbackground="#E2E8F0")
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0, 20))
        btn = tk.Button(row, text=btn_txt, font=("Inter", 10, "bold"), bg="#F1F5F9", relief="flat",
                  padx=20, pady=8, command=cmd)
        btn.pack(side=tk.LEFT)
        btn_tips = {
            "SELECT FILE": "Open file browser",
            "Browse...": "Open file browser",
            "CHANGE LOCATION": "Choose output folder",
        }
        ToolTip(btn, btn_tips.get(btn_txt, ""))
        return entry

    def log(self, msg, level="INFO"):
        self.log_queue.put((msg, level))
        log_map = {"INFO": file_logger.info, "OK": file_logger.info, "WARN": file_logger.warning, "ERROR": file_logger.error}
        log_map.get(level, file_logger.info)(msg)

    def check_log_queue(self):
        while not self.log_queue.empty():
            item = self.log_queue.get()
            msg, level = item if isinstance(item, tuple) else (item, "INFO")
            try:
                tag = f"log_{level}"
                if tag not in self.log_area.tag_names():
                    self.log_area.tag_configure(tag, foreground=LOG_COLORS.get(level, "#10B981"))
                prefix = {"WARN": "[WARN] ", "ERROR": "[ERR] ", "OK": "", "INFO": ""}.get(level, "")
                self.log_area.insert(tk.END,
                    f"[{datetime.now().strftime('%H:%M:%S')}] {prefix}{msg}\n", tag)
                self.log_area.see(tk.END)
            except (tk.TclError, AttributeError):
                pass
        self.root.after(100, self.check_log_queue)

    def copy_logs(self):
        try:
            logs = self.log_area.get(1.0, tk.END)
            self.root.clipboard_clear()
            self.root.clipboard_append(logs)
            self.status_msg.set("Logs copied to clipboard!")
            self.root.after(2000, lambda: self.status_msg.set("Ready"))
        except (tk.TclError, AttributeError):
            pass

    def _debounced_search(self):
        if self._search_after_id:
            self.root.after_cancel(self._search_after_id)
        self._search_after_id = self.root.after(300, self.refresh_history)

    def refresh_history(self):
        if hasattr(self, 'tree') and self.active_tab == "HISTORY":
            for i in self.tree.get_children():
                self.tree.delete(i)
            for h in get_recent_history(self.search_var.get()):
                full_path = h[6] if h[6] else h[4]
                self.tree.insert("", tk.END, values=(h[1], h[2], h[3], h[5]),
                                 tags=(h[4], full_path))

    def open_sel(self):
        sel = self.tree.selection()
        if sel:
            tags = self.tree.item(sel[0], "tags")
            path = tags[0] if tags else ""
            if os.path.exists(path):
                open_path(path)
            else:
                messagebox.showwarning("Not Found", f"Path no longer exists:\n{path}")

    def re_run_history(self):
        sel = self.tree.selection()
        if not sel:
            return
        tags = self.tree.item(sel[0], "tags")
        full_path = tags[1] if len(tags) > 1 and tags[1] else ""
        item_vals = self.tree.item(sel[0], "values")
        if not item_vals:
            return
        audit_type = item_vals[3]  # "Type" column

        if not full_path or not os.path.exists(full_path):
            messagebox.showwarning("File Not Found",
                                   f"The original Excel file is no longer available:\n{full_path}")
            return

        is_equitas = audit_type and "EQUITAS" in audit_type.upper()
        target_bank = "Equitas Small Finance Bank" if is_equitas else "IDFC First Bank"

        if is_equitas:
            clean_type = audit_type.replace(" (CANCELLED)", "")
            self.equitas_stage_var.set("STAGE 1" if clean_type == "Equitas-S1" else "STAGE 2")

        if self.bank_var.get() != target_bank:
            self.bank_var.set(target_bank)
            self.on_bank_change(preserve_file=full_path)
        else:
            self.file_var.set(full_path)

        self.switch_tab("PROCESS")
        self.root.after(100, lambda: self.status_msg.set("Loaded from history — ready to run"))

    def export_history(self):
        import pandas as pd
        f = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if f:
            try:
                data = get_recent_history(limit=1000)
                df = pd.DataFrame(data, columns=["ID", "Timestamp", "Filename", "Items", "Path", "Type", "SourceFile"])
                df.to_excel(f, index=False)
                messagebox.showinfo("Success", "History exported!")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))

    def _show_summary(self, title, lines):
        """Show a generation summary in a custom dialog."""
        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(bg="#FFFFFF")
        win.geometry("520x400")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        container = tk.Frame(win, bg="#FFFFFF", padx=30, pady=25)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(container, text=title, font=("Inter", 16, "bold"),
                 bg="#FFFFFF", fg="#0F172A").pack(anchor="w", pady=(0, 15))

        text = tk.Text(container, font=("Menlo", 10), bg="#F8FAFC", fg="#1E293B",
                       relief="flat", highlightthickness=1, highlightbackground="#E2E8F0",
                       padx=15, pady=15, height=10, wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True)
        for level, msg in lines:
            tag = f"sum_{level}"
            color = {"info": "#475569", "ok": "#16A34A", "warn": "#D97706", "err": "#DC2626"}.get(level, "#475569")
            text.tag_configure(tag, foreground=color)
            text.insert(tk.END, msg + "\n", tag)
        text.configure(state=tk.DISABLED)

        btn_frame = tk.Frame(container, bg="#FFFFFF", pady=(15, 0))
        btn_frame.pack(fill=tk.X)
        tk.Button(btn_frame, text="Close", font=("Inter", 10, "bold"),
                  bg="#F1F5F9", relief="flat", padx=30, pady=8,
                  command=win.destroy).pack(side=tk.RIGHT)

    def _on_close(self):
        if self.btn_run and self.btn_run.cget("state") == tk.DISABLED:
            if not messagebox.askyesno("Exit?", "A generation is in progress. Exit anyway? Partial results may be lost."):
                return
            self.cancel_event.set()
        # If there's a pending update (batch script waiting for us to exit),
        # inform the user that the update will apply now.
        if self._pending_update_bat:
            file_logger.info("Exiting with pending update — batch script will apply it.")
        self.root.update_idletasks()
        self.root.destroy()
        # sys.exit runs atexit handlers → PyInstaller cleans up _MEI temp dir
        # If an update batch script is waiting, it will detect our exit,
        # copy the new exe, clean up, and relaunch.
        sys.exit(0)

    def cancel_process(self):
        if not messagebox.askyesno("Confirm Cancel", "Are you sure you want to stop the current generation?\nPartial results will be saved."):
            return
        self.cancel_event.set()
        self.btn_cancel.config(state=tk.DISABLED, text="Stop")
        self.log("Cancel requested — stopping safely...", "WARN")

    def update_progress(self, val):
        self.root.after(0, lambda: self.progress_var.set(val))
        self.root.after(0, lambda: self.prog_label.config(text=f"{int(val)}%"))

    # ---------------------------------------------------------
    # PROCESS ENGINE - IDFC
    # ---------------------------------------------------------
    def start_process_idfc(self):
        inp = self.file_var.get().strip()
        out = self.folder_var.get().strip()
        typ = self.typ_var.get().strip()

        if not inp:
            return messagebox.showerror("Error", "Please select an Excel file.")
        valid, err = pdf_logic.validate_excel(inp)
        if not valid:
            return messagebox.showerror("Validation Error", err)
        if not out:
            return messagebox.showerror("Error", "Please select an output directory.")
        valid, err = pdf_logic.validate_output_dir(out)
        if not valid:
            return messagebox.showerror("Output Error", err)

        self.cancel_event.clear()
        self.btn_run.config(state=tk.DISABLED, text="Processing...")
        self.btn_cancel.config(state=tk.NORMAL, text="Stop")
        set_config("auto_open", str(self.auto_open.get()))
        try:
            self.log_area.delete(1.0, tk.END)
        except (tk.TclError, AttributeError):
            pass
        self.progress_var.set(0)
        self.status_msg.set("Processing...")

        threading.Thread(target=self.worker_idfc, args=(inp, out, typ), daemon=True).start()

    def worker_idfc(self, inp, out_base, typ):
        try:
            inp = os.path.abspath(os.path.normpath(inp))
            out_base = os.path.abspath(os.path.normpath(out_base))

            excel_name = os.path.splitext(os.path.basename(inp))[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            out = os.path.join(out_base, f"{excel_name}_{timestamp}")
            out = os.path.abspath(os.path.normpath(out))
            os.makedirs(out, exist_ok=True)

            self.log(f"Initializing Build: {excel_name}")
            s, h, rows = pdf_logic.read_excel(inp, self.log)
            groups = pdf_logic.group_by_branch(rows)

            total = len(groups)
            count = 0
            needs_zip = self.pkg_var.get() in ("ZIP ONLY", "BOTH")
            pdf_pct_max = 90.0 if needs_zip else 100.0

            # ETA tracking
            import time as _time
            _start_time = _time.time()
            _per_item_times = []

            for c, br in sorted(groups.items()):
                if self.cancel_event.is_set():
                    self.log(f"CANCELLED by user after {count}/{total} branches.", "WARN")
                    break

                name = str(br[0].get("CurrentBranchName", "Branch")).strip()
                st = str(br[0].get("State", "")).strip()
                safe_name = "".join(x for x in name if x.isalnum() or x in " -_").strip()
                if not safe_name:
                    safe_name = str(c)
                naming_pattern = get_config("naming_pattern", "{branch}_{type}")
                branch_part = safe_name
                type_part = typ
                filename = naming_pattern.replace("{branch}", branch_part).replace("{type}", type_part)
                filename = "".join(x for x in filename if x.isalnum() or x in " -_.").strip()
                if not filename.endswith(".pdf"):
                    filename += ".pdf"
                path = os.path.join(out, filename)
                path = os.path.abspath(os.path.normpath(path))

                self.root.after(0, lambda n=safe_name: self.branch_label.config(text=f"▶ Building: {n}"))
                self.log(f"Building: {safe_name}")
                pdf_logic.generate_pdf(typ, c, name, st, br, path)
                count += 1

                prog = (count / total) * pdf_pct_max
                self.update_progress(prog)

                # ETA calculation
                elapsed = _time.time() - _start_time
                _per_item_times.append(elapsed / count)
                avg_time = sum(_per_item_times) / len(_per_item_times)
                remaining = avg_time * (total - count)
                if remaining > 60:
                    self.status_msg.set(f"Processing {count}/{total} — ~{int(remaining//60)}m {int(remaining%60)}s remaining")
                else:
                    self.status_msg.set(f"Processing {count}/{total} — ~{int(remaining)}s remaining")

            self.root.after(0, lambda: self.branch_label.config(text=""))
            was_cancelled = self.cancel_event.is_set()

            if not was_cancelled:
                log_generation(excel_name, count, out, typ, full_path=inp)
                _elapsed = _time.time() - _start_time
                self.log(f"SUCCESS: {count} Reports Created in {_elapsed:.1f}s.", "OK")

                mode = self.pkg_var.get()
                zip_path = f"{out}.zip"

                if mode in ("ZIP ONLY", "BOTH"):
                    try:
                        self.log("Compressing files...")
                        self.update_progress(92)
                        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                            for root_dir, _, files in os.walk(out):
                                for file in files:
                                    zipf.write(os.path.join(root_dir, file), file)
                        self.update_progress(97)
                        self.log(f"ZIP READY: {os.path.basename(zip_path)}", "OK")
                    except OSError as ze:
                        self.log(f"Zip Error: {ze}", "ERROR")

                if mode == "ZIP ONLY":
                    try:
                        self.log("Cleaning up raw PDFs (Space Saved)...")
                        import shutil
                        shutil.rmtree(out)
                    except OSError as re:
                        self.log(f"Cleanup Error: {re}", "ERROR")

                self.update_progress(100)

                # Calculate total output size
                final_target = zip_path if (mode == "ZIP ONLY" and os.path.exists(zip_path)) else out
                total_size = 0
                if os.path.isfile(final_target):
                    total_size = os.path.getsize(final_target)
                elif os.path.isdir(final_target):
                    for root_dir, _, files in os.walk(final_target):
                        for f in files:
                            total_size += os.path.getsize(os.path.join(root_dir, f))

                size_str = f"{total_size / 1024:.1f} KB" if total_size < 1024*1024 else f"{total_size / 1024 / 1024:.1f} MB"
                self.log(f"Total output size: {size_str}", "INFO")

                if self.auto_open.get():
                    if os.path.exists(final_target):
                        open_path(final_target)

                summary_lines = [
                    ("ok", f"✓ {count} PDFs generated successfully"),
                    ("info", f"  Audit type: {typ}"),
                    ("info", f"  Branches:   {count}"),
                    ("info", f"  Time:       {_elapsed:.1f}s"),
                    ("info", f"  Size:       {size_str}"),
                    ("info", f"  Output:     {final_target}"),
                ]
                self.root.after(0, lambda: self._show_summary("Generation Complete", summary_lines))
            else:
                log_generation(excel_name, count, out, f"{typ} (CANCELLED)", full_path=inp)
                self.root.after(0, lambda: messagebox.showwarning("Cancelled", f"Stopped after {count}/{total} branches."))

        except Exception as e:
            self.log(f"FAILURE: {e}", "ERROR")
            self.root.after(0, lambda: messagebox.showerror("Failure", str(e)))
        finally:
            self.root.after(0, lambda: self.branch_label.config(text=""))
            self.root.after(0, lambda: self.btn_run.config(state=tk.NORMAL, text="Generate Reports"))
            self.root.after(0, lambda: self.btn_cancel.config(state=tk.DISABLED, text="Stop"))
            self.root.after(0, lambda: self.status_msg.set("Ready"))
            self.root.after(0, self.refresh_history)
            self.cancel_event.clear()

    # ---------------------------------------------------------
    # PROCESS ENGINE - EQUITAS
    # ---------------------------------------------------------
    def start_process_equitas(self):
        inp = self.file_var.get().strip()
        out = self.folder_var.get().strip()
        stage = self.equitas_stage_var.get()

        if not inp:
            return messagebox.showerror("Error", "Please select an Excel file.")

        if stage == "STAGE 1":
            valid, err = equitas_logic.validate_equitas_stage1_file(inp)
        else:
            valid, err = equitas_logic.validate_equitas_stage2_file(inp)

        if not valid:
            return messagebox.showerror("Validation Error", err)

        if not out:
            return messagebox.showerror("Error", "Please select an output directory.")

        valid, err = pdf_logic.validate_output_dir(out)
        if not valid:
            return messagebox.showerror("Output Error", err)

        self.cancel_event.clear()
        self.btn_run.config(state=tk.DISABLED, text="Processing...")
        self.btn_cancel.config(state=tk.NORMAL, text="Stop")
        set_config("auto_open", str(self.auto_open.get()))
        try:
            self.log_area.delete(1.0, tk.END)
        except (tk.TclError, AttributeError):
            pass
        self.progress_var.set(0)
        self.status_msg.set(f"Processing Equitas {stage}...")

        threading.Thread(target=self.worker_equitas, args=(inp, out, stage), daemon=True).start()

    def worker_equitas(self, inp, out_base, stage):
        try:
            inp = os.path.abspath(os.path.normpath(inp))
            out_base = os.path.abspath(os.path.normpath(out_base))

            excel_name = os.path.splitext(os.path.basename(inp))[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            out = os.path.join(out_base, f"{excel_name}_EQ_{stage.replace(' ', '')}_{timestamp}")
            out = os.path.abspath(os.path.normpath(out))
            os.makedirs(out, exist_ok=True)

            self.log(f"Initializing Equitas {stage}: {excel_name}")

            if stage == "STAGE 1":
                fmt = self.equitas_format_var.get()
                pack = self.equitas_pack_var.get()
                import time as _time
                _eqs1_start = _time.time()
                pdf_c, exc_c = equitas_logic.run_equitas_stage1(
                    inp, out, self.log, self.cancel_event, self.update_progress,
                    output_format=fmt, output_mode=pack
                )
                _eqs1_elapsed = _time.time() - _eqs1_start
                was_cancelled = self.cancel_event.is_set()

                if not was_cancelled:
                    log_generation(excel_name, pdf_c + exc_c, out, "Equitas-S1", full_path=inp)
                    self.log(f"SUCCESS: {pdf_c} PDFs, {exc_c} Excels created. ({_eqs1_elapsed:.1f}s)", "OK")
                    self.update_progress(100)

                    # Calculate output size
                    total_size = 0
                    for root_dir, _, files in os.walk(out):
                        for f in files:
                            total_size += os.path.getsize(os.path.join(root_dir, f))
                    size_str = f"{total_size / 1024:.1f} KB" if total_size < 1024*1024 else f"{total_size / 1024 / 1024:.1f} MB"

                    if self.auto_open.get():
                        open_path(out)

                    summary = [
                        ("ok", f"✓ Stage 1 Complete — {pdf_c} PDFs, {exc_c} Excels"),
                        ("info", f"  Time:  {_eqs1_elapsed:.1f}s"),
                        ("info", f"  Size:  {size_str}"),
                        ("info", f"  Path:  {out}"),
                    ]
                    self.root.after(0, lambda: self._show_summary("Stage 1 Complete", summary))
                else:
                    log_generation(excel_name, pdf_c + exc_c, out, "Equitas-S1 (CANCELLED)", full_path=inp)
                    self.root.after(0, lambda: messagebox.showwarning("Cancelled", "Stage 1 Generation Cancelled."))

            else:
                out_path = equitas_logic.run_equitas_stage2(
                    inp, out, self.log, self.cancel_event, self.update_progress
                )
                was_cancelled = self.cancel_event.is_set()

                if not was_cancelled and out_path:
                    log_generation(excel_name, 1, out_path, "Equitas-S2", full_path=inp)
                    total_size = os.path.getsize(out_path) if os.path.isfile(out_path) else 0
                    size_str = f"{total_size / 1024:.1f} KB" if total_size < 1024*1024 else f"{total_size / 1024 / 1024:.1f} MB"
                    self.log(f"SUCCESS: Consolidated report created. ({size_str})", "OK")
                    self.update_progress(100)

                    if self.auto_open.get():
                        open_path(out)

                    summary = [
                        ("ok", "✓ Stage 2 Consolidation Complete"),
                        ("info", f"  Size:  {size_str}"),
                        ("info", f"  Path:  {out_path}"),
                    ]
                    self.root.after(0, lambda: self._show_summary("Stage 2 Complete", summary))
                else:
                    log_generation(excel_name, 0, out, "Equitas-S2 (CANCELLED)", full_path=inp)
                    self.root.after(0, lambda: messagebox.showwarning("Cancelled", "Stage 2 Consolidation Cancelled."))

        except Exception as e:
            self.log(f"FAILURE: {e}", "ERROR")
            self.root.after(0, lambda: messagebox.showerror("Failure", str(e)))
        finally:
            btn_text = "Generate (Stage 1)" if stage == "STAGE 1" else "Consolidate (Stage 2)"
            self.root.after(0, lambda: self.btn_run.config(state=tk.NORMAL, text=btn_text))
            self.root.after(0, lambda: self.btn_cancel.config(state=tk.DISABLED, text="Stop"))
            self.root.after(0, lambda: self.status_msg.set("Ready"))
            self.root.after(0, self.refresh_history)
            self.cancel_event.clear()


if __name__ == "__main__":
    # Required for PyInstaller frozen executables on Windows —
    # prevents pyi_rth_multiprocessing runtime hook crashes
    import multiprocessing
    multiprocessing.freeze_support()

    root = tk.Tk()
    app = App(root)
    root.mainloop()

