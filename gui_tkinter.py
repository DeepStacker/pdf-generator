import os
import sys
import time
import json
import re
import zipfile
import io
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime
import threading
import traceback
import subprocess
import platform
import urllib.request
import urllib.error
import webbrowser
import queue

import pdf_logic
import equitas_logic

VERSION = "5.2.206"

MONO_FONT = "SF Mono" if platform.system() == "Darwin" else "Consolas"

CONFIG_FILE = os.path.expanduser("~/.audit_engine_config.json")
DEFAULT_OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "AuditEngine_Reports")
MAX_RECENT = 8
GITHUB_REPO = "DeepStacker/pdf-generator"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases"
GITHUB_RELEASES = f"https://github.com/{GITHUB_REPO}/releases"
TK_TAG_PREFIX = "tk-"


def _load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_config(cfg):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f)
    except OSError:
        pass


def _format_size(n):
    for unit in ("B", "KB", "MB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def _open_folder(path):
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
    except Exception:
        pass


def _clean_tag(tag):
    for prefix in ("tk-v", "tk-", "v"):
        if tag.startswith(prefix):
            return tag[len(prefix):]
    return tag


def _fetch_latest_tk_release():
    req = urllib.request.Request(
        GITHUB_API,
        headers={"User-Agent": "AuditEngine/5.0", "Accept": "application/vnd.github.v3+json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        releases = json.loads(resp.read().decode())
    for r in releases:
        tag = r.get("tag_name", "")
        if tag.startswith(TK_TAG_PREFIX):
            return r
    return None


class AuditEngineGUI:
    COLORS = {
        "bg": "#0f172a",
        "fg": "#e2e8f0",
        "card": "#1e293b",
        "card_border": "#334155",
        "accent": "#3b82f6",
        "accent_hover": "#2563eb",
        "success": "#22c55e",
        "warning": "#f59e0b",
        "error": "#ef4444",
        "input_bg": "#1e293b",
        "input_fg": "#f1f5f9",
        "text_muted": "#64748b",
        "log_bg": "#0b1120",
        "log_fg": "#94a3b8",
        "header_bg": "#1e293b",
        "progress_bg": "#334155",
        "progress_fill": "#3b82f6",
        "btn_text": "#ffffff",
        "btn_bg": "#3b82f6",
        "btn_hover": "#2563eb",
        "btn_success": "#16a34a",
        "btn_success_hover": "#15803d",
        "btn_danger": "#ef4444",
        "btn_danger_hover": "#dc2626",
        "btn_outline": "transparent",
        "btn_outline_text": "#94a3b8",
        "tooltip_bg": "#1e293b",
    }

    def __init__(self):
        self.cfg = _load_config()
        self._last_output_dir = None
        self._start_time = None
        self._timer_active = False
        self._cancel_event = threading.Event()
        self._log_queue = queue.Queue()

        self.root = tk.Tk()
        self.root.title("Audit Engine Elite")
        self.root.configure(bg=self.COLORS["bg"])
        self.root.minsize(820, 620)

        geo = self.cfg.get("window_geo", "960x740")
        try:
            self.root.geometry(geo)
        except tk.TclError:
            self.root.geometry("960x740")

        self._style_ttk()
        self._latest_ver = tk.StringVar(value="")
        self.progress_pct_var = tk.StringVar(value="0%")
        self.root.after(100, self._flush_log_queue)

        self._style_ttk()
        self._latest_ver = tk.StringVar(value="")

        # variables
        self.file_path = tk.StringVar()
        self.output_dir = tk.StringVar(value=self.cfg.get("output_dir", DEFAULT_OUTPUT_DIR))
        self.idfc_audit_type = tk.StringVar(value=self.cfg.get("idfc_type", "TAF"))
        self.eq_format = tk.StringVar(value=self.cfg.get("eq_format", "BOTH"))
        self.eq_mode = tk.StringVar(value=self.cfg.get("eq_mode", "FOLDER"))
        self.progress_var = tk.DoubleVar()
        self.status_text = tk.StringVar(value="Ready")
        self.current_op = tk.StringVar()
        self.elapsed_text = tk.StringVar()

        # ── Header ──
        header = tk.Frame(self.root, bg=self.COLORS["header_bg"], height=64)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(header, text="\u2699", font=("Segoe UI", 24),
                 fg=self.COLORS["accent"], bg=self.COLORS["header_bg"]).pack(side=tk.LEFT, padx=(18, 6))

        self.status_dot = tk.Label(header, text="\u25cf", font=("Segoe UI", 10),
                                    fg=self.COLORS["success"], bg=self.COLORS["header_bg"])
        self.status_dot.pack(side=tk.LEFT, padx=(0, 2))
        self._make_tooltip(self.status_dot, "Ready")

        tfr = tk.Frame(header, bg=self.COLORS["header_bg"])
        tfr.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(8, 0))
        tk.Label(tfr, text="Audit Engine Elite", font=("Segoe UI", 17, "bold"),
                 fg="#ffffff", bg=self.COLORS["header_bg"], anchor="w").pack(anchor="w")
        tk.Label(tfr, text="Professional PDF Report Generator  \u2022  Ctrl+O Browse  \u2022  Ctrl+R Run",
                 font=("Segoe UI", 9), fg=self.COLORS["text_muted"],
                 bg=self.COLORS["header_bg"], anchor="w").pack(anchor="w")

        hbtn_frame = tk.Frame(header, bg=self.COLORS["header_bg"])
        hbtn_frame.pack(side=tk.RIGHT, padx=(0, 14))

        self.btn_update = ttk.Button(hbtn_frame, text="\u2b06 Check Update",
                                      command=self._check_updates, style="Small.TButton")
        self.btn_update.pack(side=tk.LEFT, padx=(0, 6))
        self._make_tooltip(self.btn_update, "Check for updates on GitHub")

        self.btn_open_output = ttk.Button(hbtn_frame, text="\U0001f4c2 Open Output",
                                           command=self._open_output, style="Small.TButton")
        self.btn_open_output.pack(side=tk.LEFT, padx=(0, 6))
        self._make_tooltip(self.btn_open_output, "Open the output reports folder")

        self.btn_dl = ttk.Button(hbtn_frame, text="\u2b07 Download Latest",
                                  command=self._download_latest, style="Small.TButton")
        self.btn_dl.pack(side=tk.LEFT, padx=(0, 6))
        self._make_tooltip(self.btn_dl, "Download & install latest version from GitHub")

        self.btn_clear_log = ttk.Button(hbtn_frame, text="\u2716 Clear Log (Ctrl+L)",
                                         command=self._clear_log, style="Small.TButton")
        self.btn_clear_log.pack(side=tk.LEFT)

        # ── Main ──
        main = tk.Frame(self.root, bg=self.COLORS["bg"])
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=(14, 10))

        # ── Row: Input + Output cards ──
        row_top = tk.Frame(main, bg=self.COLORS["bg"])
        row_top.pack(fill=tk.X, pady=(0, 10))

        # Input card (left 60%)
        card_in = tk.Frame(row_top, bg=self.COLORS["card"],
                           highlightbackground=self.COLORS["card_border"],
                           highlightthickness=1, padx=14, pady=12)
        card_in.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        tk.Label(card_in, text="Input Excel File", font=("Segoe UI", 11, "bold"),
                 fg=self.COLORS["fg"], bg=self.COLORS["card"]).pack(anchor="w")
        row = tk.Frame(card_in, bg=self.COLORS["card"])
        row.pack(fill=tk.X, pady=(6, 2))
        self.entry = ttk.Entry(row, textvariable=self.file_path, style="TEntry")
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.btn_browse = ttk.Button(row, text="Browse...", command=self._browse_file)
        self.btn_browse.pack(side=tk.RIGHT)

        self.file_info_label = tk.Label(card_in, text="", font=("Segoe UI", 9, "italic"),
                                         fg=self.COLORS["text_muted"], bg=self.COLORS["card"],
                                         anchor="w")
        self.file_info_label.pack(fill=tk.X, pady=(2, 0))

        recent = self.cfg.get("recent", [])
        if recent:
            self.recent_cb = ttk.Combobox(card_in, values=["Recent files..."] + recent,
                                           state="readonly", width=30)
            self.recent_cb.current(0)
            self.recent_cb.pack(fill=tk.X, pady=(4, 0))
            self.recent_cb.bind("<<ComboboxSelected>>", self._on_recent_selected)
            self._make_tooltip(self.recent_cb, "Select a recently opened file")

        # Output card (right ~40%)
        card_out = tk.Frame(row_top, bg=self.COLORS["card"],
                            highlightbackground=self.COLORS["card_border"],
                            highlightthickness=1, padx=14, pady=12)
        card_out.pack(side=tk.RIGHT, fill=tk.X)

        tk.Label(card_out, text="Output Directory", font=("Segoe UI", 11, "bold"),
                 fg=self.COLORS["fg"], bg=self.COLORS["card"]).pack(anchor="w")
        orow = tk.Frame(card_out, bg=self.COLORS["card"])
        orow.pack(fill=tk.X, pady=(6, 0))
        self.out_entry = ttk.Entry(orow, textvariable=self.output_dir, style="TEntry")
        self.out_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.btn_out = ttk.Button(orow, text="...", width=3, command=self._browse_output)
        self.btn_out.pack(side=tk.RIGHT)

        # ── Action card ──
        card_act = tk.Frame(main, bg=self.COLORS["card"],
                            highlightbackground=self.COLORS["card_border"],
                            highlightthickness=1, padx=14, pady=10)
        card_act.pack(fill=tk.X, pady=(0, 10))

        act_header = tk.Frame(card_act, bg=self.COLORS["card"])
        act_header.pack(fill=tk.X)
        tk.Label(act_header, text="Actions", font=("Segoe UI", 11, "bold"),
                 fg=self.COLORS["fg"], bg=self.COLORS["card"]).pack(side=tk.LEFT)

        opts = tk.Frame(card_act, bg=self.COLORS["card"])
        opts.pack(fill=tk.X, pady=(6, 0))

        tk.Label(opts, text="IDFC Type:", font=("Segoe UI", 9),
                 fg=self.COLORS["text_muted"], bg=self.COLORS["card"]).pack(side=tk.LEFT, padx=(0, 4))

        for val, tt in (("POA", "Power of Attorney audit type for IDFC PDF reports"),
                         ("TAF", "TAF audit type for IDFC PDF reports")):
            rb = tk.Radiobutton(opts, text=val, variable=self.idfc_audit_type, value=val,
                                font=("Segoe UI", 9), fg=self.COLORS["fg"],
                                bg=self.COLORS["card"], selectcolor=self.COLORS["card"],
                                activebackground=self.COLORS["card"],
                                activeforeground=self.COLORS["accent"],
                                highlightthickness=0, borderwidth=0)
            rb.pack(side=tk.LEFT, padx=(0, 12))
            self._make_tooltip(rb, tt)

        tk.Label(opts, text="  Equitas Format:", font=("Segoe UI", 9),
                 fg=self.COLORS["text_muted"], bg=self.COLORS["card"]).pack(side=tk.LEFT, padx=(0, 4))
        fmt_cb = ttk.Combobox(opts, textvariable=self.eq_format, width=12,
                               values=["PDF ONLY", "EXCEL ONLY", "BOTH"], state="readonly")
        fmt_cb.pack(side=tk.LEFT, padx=(0, 16))
        self._make_tooltip(fmt_cb, "Output format for Equitas processing")

        tk.Label(opts, text="Mode:", font=("Segoe UI", 9),
                 fg=self.COLORS["text_muted"], bg=self.COLORS["card"]).pack(side=tk.LEFT, padx=(0, 4))
        mode_cb = ttk.Combobox(opts, textvariable=self.eq_mode, width=18,
                                values=["FOLDER", "ZIP OF BOTH", "BOTH (FOLDER + ZIP OF PDF)"],
                                state="readonly")
        mode_cb.pack(side=tk.LEFT)
        self._make_tooltip(mode_cb, "ZIP packaging mode for Equitas output")

        sep = tk.Frame(card_act, bg=self.COLORS["card_border"], height=1)
        sep.pack(fill=tk.X, pady=(10, 0))

        btn_row = tk.Frame(card_act, bg=self.COLORS["card"])
        btn_row.pack(fill=tk.X, pady=(8, 0))

        self.btn_idfc = ttk.Button(btn_row, text="\u25b6  Process IDFC",
                                    command=lambda: self._run("idfc"), style="Success.TButton")
        self.btn_idfc.pack(side=tk.LEFT, padx=(0, 6))
        self._make_tooltip(self.btn_idfc, "Ctrl+R  |  Generate IDFC PDF reports")

        self.btn_eq1 = ttk.Button(btn_row, text="\u25b6  Equitas Stage 1",
                                   command=lambda: self._run("equitas1"))
        self.btn_eq1.pack(side=tk.LEFT, padx=(0, 6))
        self._make_tooltip(self.btn_eq1, "Ctrl+R  |  Process Equitas Master Excel")

        self.btn_eq2 = ttk.Button(btn_row, text="\u25b6  Equitas Stage 2",
                                   command=lambda: self._run("equitas2"))
        self.btn_eq2.pack(side=tk.LEFT, padx=(0, 6))
        self._make_tooltip(self.btn_eq2, "Ctrl+R  |  Consolidate Equitas Stage 1 output")

        self.btn_cancel = ttk.Button(btn_row, text="\u2716 Cancel",
                                      command=self._cancel, style="Danger.TButton")
        self.btn_cancel.pack(side=tk.RIGHT)
        self._make_tooltip(self.btn_cancel, "Stop current operation (Ctrl+Shift+X)")

        # ── Progress section ──
        prog_frame = tk.Frame(main, bg=self.COLORS["bg"])
        prog_frame.pack(fill=tk.X, pady=(0, 6))

        self.progress_bar = ttk.Progressbar(prog_frame, mode="determinate",
                                              variable=self.progress_var)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.progress_pct_label = tk.Label(prog_frame, textvariable=self.progress_pct_var,
                                             font=("Segoe UI", 9, "bold"),
                                             fg=self.COLORS["accent"], bg=self.COLORS["bg"],
                                             width=5, anchor="e")
        self.progress_pct_label.pack(side=tk.RIGHT, padx=(8, 0))

        self.elapsed_label = tk.Label(prog_frame, textvariable=self.elapsed_text,
                                        font=("Segoe UI", 9), fg=self.COLORS["text_muted"],
                                        bg=self.COLORS["bg"], anchor="e", width=10)
        self.elapsed_label.pack(side=tk.RIGHT, padx=(4, 0))

        self.status_label = tk.Label(main, textvariable=self.status_text,
                                      font=("Segoe UI", 10, "bold"),
                                      fg=self.COLORS["accent"], bg=self.COLORS["bg"],
                                      anchor="w")
        self.status_label.pack(fill=tk.X)

        self.op_label = tk.Label(main, textvariable=self.current_op,
                                  font=("Segoe UI", 9),
                                  fg=self.COLORS["text_muted"], bg=self.COLORS["bg"],
                                  anchor="w")
        self.op_label.pack(fill=tk.X, pady=(0, 6))

        sep2 = tk.Frame(main, bg=self.COLORS["card_border"], height=1)
        sep2.pack(fill=tk.X, pady=(0, 8))

        # ── Log card ──
        card_log = tk.Frame(main, bg=self.COLORS["card"],
                            highlightbackground=self.COLORS["card_border"],
                            highlightthickness=1, padx=14, pady=10)
        card_log.pack(fill=tk.BOTH, expand=True)

        lhdr = tk.Frame(card_log, bg=self.COLORS["card"])
        lhdr.pack(fill=tk.X)
        tk.Label(lhdr, text="Output Log", font=("Segoe UI", 11, "bold"),
                 fg=self.COLORS["fg"], bg=self.COLORS["card"]).pack(side=tk.LEFT)
        tk.Label(lhdr, text="\u2022 right-click for options  \u2022  Ctrl+L clear",
                 font=("Segoe UI", 8), fg=self.COLORS["text_muted"],
                 bg=self.COLORS["card"]).pack(side=tk.RIGHT)

        lc = tk.Frame(card_log, bg=self.COLORS["card"])
        lc.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        self.log_text = tk.Text(lc, wrap=tk.WORD, state=tk.NORMAL,
                                 bg=self.COLORS["log_bg"], fg=self.COLORS["log_fg"],
                                 font=(MONO_FONT, 9), relief="flat", borderwidth=0,
                                 padx=10, pady=8, insertbackground=self.COLORS["accent"],
                                 highlightbackground=self.COLORS["card_border"])
        self.log_text.tag_configure("file", foreground=self.COLORS["accent"])
        self.log_text.tag_configure("warn", foreground=self.COLORS["warning"])
        self.log_text.tag_configure("error", foreground=self.COLORS["error"])
        self.log_text.tag_configure("success", foreground=self.COLORS["success"])
        self.log_text.tag_configure("ts", foreground=self.COLORS["text_muted"])

        vsb = tk.Scrollbar(lc, orient=tk.VERTICAL, command=self.log_text.yview,
                            bg=self.COLORS["card_border"], troughcolor=self.COLORS["card"])
        self.log_text.configure(yscrollcommand=vsb.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self._log("Audit Engine GUI ready. Select an Excel file and click a processing button.",
                  "success")

        # ── Footer ──
        footer = tk.Frame(self.root, bg=self.COLORS["bg"], height=24)
        footer.pack(fill=tk.X)

        self.footer_ver = tk.Label(footer,
                                    text=f"\u2b06 v{VERSION}  \u2014  100% Offline  \u2022  Ctrl+O Browse  \u2022  Ctrl+R Run",
                                    font=("Segoe UI", 8), fg=self.COLORS["text_muted"],
                                    bg=self.COLORS["bg"])
        self.footer_ver.pack(side=tk.LEFT, pady=(3, 0))
        self.footer_ver.bind("<Button-1>", lambda e: self._check_updates())

        self._setup_log_context_menu()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._bind_shortcuts()
        self.root.after(2000, self._startup_update_check)

    def _style_ttk(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", font=("Segoe UI", 10, "bold"),
                        background=self.COLORS["btn_bg"], foreground=self.COLORS["btn_text"],
                        borderwidth=0, focuscolor="none", relief="flat",
                        padding=(16, 6))
        style.map("TButton",
                   background=[("active", self.COLORS["btn_hover"])],
                   foreground=[("active", self.COLORS["btn_text"])])
        style.configure("Success.TButton",
                         background=self.COLORS["btn_success"],
                         foreground=self.COLORS["btn_text"])
        style.map("Success.TButton",
                   background=[("active", self.COLORS["btn_success_hover"])],
                   foreground=[("active", self.COLORS["btn_text"])])
        style.configure("Danger.TButton",
                         background=self.COLORS["btn_danger"],
                         foreground=self.COLORS["btn_text"])
        style.map("Danger.TButton",
                   background=[("active", self.COLORS["btn_danger_hover"])],
                   foreground=[("active", self.COLORS["btn_text"])])
        style.configure("Small.TButton",
                         font=("Segoe UI", 9), padding=(10, 3))
        style.configure("TEntry",
                         fieldbackground=self.COLORS["input_bg"],
                         foreground=self.COLORS["input_fg"],
                         insertcolor=self.COLORS["input_fg"],
                         borderwidth=0, relief="flat", padding=(8, 6))
        style.map("TEntry",
                   fieldbackground=[("focus", self.COLORS["input_bg"])])
        style.configure("TCombobox",
                         fieldbackground=self.COLORS["input_bg"],
                         foreground=self.COLORS["input_fg"],
                         selectbackground=self.COLORS["accent"],
                         selectforeground="#ffffff",
                         borderwidth=0, arrowcolor=self.COLORS["text_muted"],
                         padding=(6, 4))
        style.map("TCombobox",
                   fieldbackground=[("readonly", self.COLORS["input_bg"])])
        style.configure("Horizontal.TProgressbar",
                         background=self.COLORS["progress_fill"],
                         troughcolor=self.COLORS["progress_bg"],
                         borderwidth=0, thickness=8)
        style.configure("TLabelframe", background=self.COLORS["card"])

    def _make_tooltip(self, widget, text):
        tw = None

        def show(e):
            nonlocal tw
            if tw:
                return
            x = e.widget.winfo_rootx() + 16
            y = e.widget.winfo_rooty() + e.widget.winfo_height() + 4
            tw = tk.Toplevel(e.widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            tw.configure(bg=self.COLORS["tooltip_bg"])
            lbl = tk.Label(tw, text=text, font=("Segoe UI", 9),
                            fg=self.COLORS["fg"], bg=self.COLORS["tooltip_bg"],
                            padx=8, pady=4)
            lbl.pack()

        def hide(e):
            nonlocal tw
            if tw:
                tw.destroy()
                tw = None

        widget.bind("<Enter>", show)
        widget.bind("<Leave>", hide)

    def _bind_shortcuts(self):
        self.root.bind("<Control-o>", lambda e: self._browse_file())
        self.root.bind("<Control-O>", lambda e: self._browse_file())
        self.root.bind("<Control-r>", lambda e: self._run_focused())
        self.root.bind("<Control-R>", lambda e: self._run_focused())
        self.root.bind("<Control-l>", lambda e: self._clear_log())
        self.root.bind("<Control-L>", lambda e: self._clear_log())
        self.root.bind("<Control-Shift-X>", lambda e: self._cancel())
        self.root.bind("<Control-Shift-x>", lambda e: self._cancel())

    def _run_focused(self):
        active = self.root.focus_get()
        if active in (self.btn_idfc, self.btn_eq1, self.btn_eq2):
            active.invoke()
            return
        btn = self.btn_idfc
        try:
            btn.configure(state=tk.NORMAL)
            btn.invoke()
        finally:
            pass

    def _log(self, msg, tag=None):
        self._log_queue.put((msg, tag))

    def _flush_log_queue(self):
        dirty = False
        while True:
            try:
                msg, tag = self._log_queue.get_nowait()
            except queue.Empty:
                break
            dirty = True
            ts = datetime.now().strftime("%H:%M:%S")
            self.log_text.insert(tk.END, f"[{ts}] ", "ts")
            self.log_text.insert(tk.END, f"{msg}\n", tag)
            self.log_text.see(tk.END)
        if dirty:
            self.root.update_idletasks()
        self.root.after(100, self._flush_log_queue)

    def _clear_log(self):
        self.log_text.delete("1.0", tk.END)
        self._log("Log cleared.", "ts")

    def _setup_log_context_menu(self):
        menu = tk.Menu(self.log_text, tearoff=0, bg=self.COLORS["card"],
                        fg=self.COLORS["fg"], activebackground=self.COLORS["accent"],
                        activeforeground="#ffffff", font=("Segoe UI", 10))
        menu.add_command(label="Copy", command=self._log_copy, accelerator="Ctrl+C")
        menu.add_command(label="Select All", command=self._log_select_all, accelerator="Ctrl+A")
        menu.add_separator()
        menu.add_command(label="Save to File...", command=self._log_save)
        menu.add_separator()
        menu.add_command(label="Clear", command=self._clear_log, accelerator="Ctrl+L")

        def show_menu(e):
            menu.tk_popup(e.x_root, e.y_root)

        self.log_text.bind("<Button-3>", show_menu)
        self.log_text.bind("<Control-Key-a>", lambda e: self._log_select_all())
        self.log_text.bind("<Control-Key-A>", lambda e: self._log_select_all())

    def _log_copy(self):
        try:
            sel = self.log_text.selection_get()
            self.root.clipboard_clear()
            self.root.clipboard_append(sel)
        except tk.TclError:
            pass

    def _log_select_all(self):
        self.log_text.tag_add(tk.SEL, "1.0", tk.END)
        self.log_text.mark_set(tk.INSERT, "1.0")
        self.log_text.see(tk.INSERT)
        return "break"

    def _log_save(self):
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save Log",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if path:
            try:
                text = self.log_text.get("1.0", tk.END)
                with open(path, "w") as f:
                    f.write(text)
                self._log(f"Log saved to {path}", "success")
            except OSError as e:
                self._log(f"Failed to save log: {e}", "error")

    def _timer_start(self):
        self._start_time = datetime.now()
        self._timer_active = True
        self._timer_tick()

    def _timer_stop(self, keep_elapsed=False):
        self._timer_active = False
        if not keep_elapsed:
            self.elapsed_text.set("")

    def _timer_tick(self):
        if not self._timer_active or not self._start_time:
            return
        delta = datetime.now() - self._start_time
        secs = int(delta.total_seconds())
        if secs < 60:
            text = f"{secs}s"
        elif secs < 3600:
            text = f"{secs // 60}m {secs % 60:02d}s"
        else:
            text = f"{secs // 3600}h {(secs % 3600) // 60:02d}m"
        self.elapsed_text.set(text)
        self.root.after(1000, self._timer_tick)

    def _browse_file(self):
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Select Excel File",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")],
        )
        if path:
            self._select_file(path)

    def _select_file(self, path):
        self.file_path.set(path)
        self._update_file_info(path)
        self._add_recent(path)

    def _update_file_info(self, path):
        try:
            size = os.path.getsize(path)
            name = os.path.basename(path)
            self.file_info_label.config(text=f"{name}  ({_format_size(size)})")
        except OSError:
            self.file_info_label.config(text="")

    def _add_recent(self, path):
        recent = self.cfg.get("recent", [])
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        self.cfg["recent"] = recent[:MAX_RECENT]
        _save_config(self.cfg)

    def _on_recent_selected(self, e):
        cb = e.widget
        val = cb.get()
        if val and val != "Recent files...":
            if os.path.isfile(val):
                self._select_file(val)
            else:
                self._log(f"File not found: {val}", "warn")
                cb.current(0)

    def _browse_output(self):
        path = filedialog.askdirectory(
            parent=self.root,
            title="Select Output Directory",
            initialdir=self.output_dir.get() or os.path.expanduser("~"),
        )
        if path:
            self.output_dir.set(path)
            self.cfg["output_dir"] = path
            _save_config(self.cfg)

    def _open_output(self):
        path = self.output_dir.get()
        if path and os.path.isdir(path):
            _open_folder(path)
        else:
            messagebox.showinfo("Output Directory",
                                f"Directory does not exist:\n{path}")

    def _startup_update_check(self):
        last_check = self.cfg.get("last_update_check", 0)
        if last_check and time.time() - last_check < 86400:
            return

        def bg_check():
            try:
                data = _fetch_latest_tk_release()
                if data is None:
                    return
                tag = _clean_tag(data.get("tag_name", ""))
                current = [int(x) for x in VERSION.split(".")]
                latest = [int(x) for x in tag.split(".")]
                while len(current) < len(latest):
                    current.append(0)
                while len(latest) < len(current):
                    latest.append(0)
                self._latest_ver.set(tag)
                update_avail = latest > current
                self.root.after(0, lambda ua=update_avail: self.footer_ver.configure(
                    text=f"\u2b06 v{VERSION}  \u2192  v{tag}  \u2014  100% Offline  \u2022  Ctrl+O Browse  \u2022  Ctrl+R Run"
                         if ua else
                         f"\u2b06 v{VERSION} (\u2192 v{tag})  \u2014  100% Offline  \u2022  Ctrl+O Browse  \u2022  Ctrl+R Run",
                    fg=self.COLORS["warning"] if ua else self.COLORS["text_muted"]))
                if update_avail:
                    self._log(f"Update available: v{VERSION} \u2192 v{tag}. Click \u2b06 to install.",
                              "warn")
                self.cfg["last_update_check"] = time.time()
                _save_config(self.cfg)
            except Exception:
                pass

        t = threading.Thread(target=bg_check, daemon=True)
        t.start()

    def _check_updates(self):
        self.btn_update.configure(text="Checking...")
        self.root.update_idletasks()

        def worker():
            try:
                data = _fetch_latest_tk_release()
                if data is None:
                    self.root.after(0, self.btn_update.configure,
                                    {"text": "\u2b06 Check Update"})
                    self.root.after(0, lambda: messagebox.showinfo(
                        "No Updates", "No tkinter release found on GitHub."))
                    return
                latest_tag = _clean_tag(data.get("tag_name", ""))
                body = data.get("body", "No release notes.")
                html_url = data.get("html_url", "")
                zipball_url = data.get("zipball_url", "")
                assets = data.get("assets", [])

                mac_asset = None
                for a in assets:
                    name = a.get("name", "")
                    if "macos" in name and name.endswith(".zip"):
                        mac_asset = a
                        break

                binary_url = mac_asset.get("browser_download_url") if mac_asset else None

                current = [int(x) for x in VERSION.split(".")]
                latest = [int(x) for x in latest_tag.split(".")]
                while len(current) < len(latest):
                    current.append(0)
                while len(latest) < len(current):
                    latest.append(0)

                self.root.after(0, self.btn_update.configure,
                                {"text": "\u2b06 Check Update"})

                print(f"[DEBUG] current={current} latest={latest} update={latest > current}")

                if latest > current:
                    self._latest_ver.set(latest_tag)
                    self.root.after(0, self._show_update_available,
                                    VERSION, latest_tag, body, html_url, zipball_url, binary_url)
                    self.root.after(0, lambda: self.footer_ver.configure(
                        text=f"\u2b06 v{VERSION}  \u2192  v{latest_tag}  \u2014  100% Offline  \u2022  Ctrl+O Browse  \u2022  Ctrl+R Run",
                        fg=self.COLORS["warning"]))
                else:
                    self._latest_ver.set(latest_tag)
                    self.root.after(0, self._show_up_to_date, VERSION)
                    self.root.after(0, lambda: self.footer_ver.configure(
                        text=f"\u2b06 v{VERSION} (\u2192 v{latest_tag})  \u2014  100% Offline  \u2022  Ctrl+O Browse  \u2022  Ctrl+R Run",
                        fg=self.COLORS["text_muted"]))

                self.cfg["last_update_check"] = time.time()
                _save_config(self.cfg)
            except Exception as e:
                import traceback as tb
                trace = tb.format_exc()
                print(f"[DEBUG] Update check failed: {e}\n{trace}")
                err = str(e)
                self.root.after(0, lambda e=err: (
                    self.btn_update.configure(text="\u2b06 Check Update"),
                    messagebox.showerror("Update Check Failed", e)
                ))

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _download_latest(self):
        self._log("Checking latest release...", "file")
        self.btn_dl.configure(text="Fetching...")
        self.root.update_idletasks()

        def worker():
            try:
                data = _fetch_latest_tk_release()
                if data is None:
                    self.root.after(0, self.btn_dl.configure, {"text": "\u2b07 Download Latest"})
                    self.root.after(0, lambda: messagebox.showinfo(
                        "No Release", "No tkinter release found on GitHub."))
                    return
                tag = data.get("tag_name", "").lstrip("v")
                url = data.get("zipball_url", "")
                if not url:
                    raise ValueError("No download URL found")
                self.root.after(0, self.btn_dl.configure, {"text": "\u2b07 Download Latest"})
                self.root.after(0, lambda: self._download_source(url, tag))
            except Exception as e:
                err = str(e)
                self.root.after(0, lambda: self.btn_dl.configure(text="\u2b07 Download Latest"))
                self._log(f"Download failed: {err}", "error")
                self.root.after(0, lambda e=err: messagebox.showerror("Download Failed", e))

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _show_up_to_date(self, version):
        messagebox.showinfo("Up to Date",
                            f"You are running the latest version (v{version}).")

    def _show_update_available(self, current_ver, latest_ver, body,
                                html_url, zipball_url, binary_url):
        try:
            win = tk.Toplevel(self.root)
            win.title("Update Available")
            win.configure(bg=self.COLORS["card"])
            win.geometry("520x400")
            win.resizable(False, False)
            win.transient(self.root)
            win.grab_set()

            tk.Label(win, text="\u2b06  Update Available",
                     font=("Segoe UI", 15, "bold"),
                     fg=self.COLORS["warning"], bg=self.COLORS["card"]).pack(pady=(14, 2))
            tk.Label(win, text=f"v{current_ver}  \u2192  v{latest_ver}",
                     font=("Segoe UI", 12),
                     fg=self.COLORS["fg"], bg=self.COLORS["card"]).pack(pady=(0, 10))

            body_frame = tk.Frame(win, bg=self.COLORS["card"],
                                   highlightbackground=self.COLORS["card_border"],
                                   highlightthickness=1)
            body_frame.pack(fill=tk.BOTH, expand=True, padx=16)

            body_text = tk.Text(body_frame, wrap=tk.WORD,
                                  bg=self.COLORS["log_bg"], fg=self.COLORS["log_fg"],
                                  font=(MONO_FONT, 9), relief="flat", borderwidth=0,
                                  padx=10, pady=8)
            body_text.insert("1.0", body)
            body_text.configure(state=tk.DISABLED)
            body_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            b_scroll = tk.Scrollbar(body_frame, orient=tk.VERTICAL, command=body_text.yview,
                                     bg=self.COLORS["card_border"], troughcolor=self.COLORS["card"])
            body_text.configure(yscrollcommand=b_scroll.set)
            b_scroll.pack(side=tk.RIGHT, fill=tk.Y)

            btn_frame = tk.Frame(win, bg=self.COLORS["card"])
            btn_frame.pack(fill=tk.X, pady=(12, 16), padx=16)

            def do_install():
                win.destroy()
                self._log(f"Downloading v{latest_ver} source...", "file")
                self.status_text.set("Downloading update...")
                self.root.update_idletasks()
                self.root.after(100, lambda: self._download_source(zipball_url, latest_ver))

            def do_github():
                webbrowser.open(html_url)
                win.destroy()

            tk.Button(btn_frame, text="\u2b07  Download & Install",
                      font=("Segoe UI", 10, "bold"),
                      bg=self.COLORS["accent"], fg="#ffffff",
                      relief="flat", padx=20, pady=6, borderwidth=0,
                      activebackground=self.COLORS["accent_hover"],
                      command=do_install
                      ).pack(side=tk.LEFT, padx=(0, 8))

            tk.Button(btn_frame, text="\U0001f517  Open on GitHub",
                      font=("Segoe UI", 10),
                      bg=self.COLORS["card_border"], fg=self.COLORS["fg"],
                      relief="flat", padx=16, pady=6, borderwidth=0,
                      command=do_github
                      ).pack(side=tk.LEFT, padx=(0, 8))

            tk.Button(btn_frame, text="Remind Later",
                      font=("Segoe UI", 10),
                      bg=self.COLORS["card_border"], fg=self.COLORS["fg"],
                      relief="flat", padx=16, pady=6, borderwidth=0,
                      command=win.destroy).pack(side=tk.RIGHT)

            win.update_idletasks()
            px = self.root.winfo_x() + (self.root.winfo_width() - win.winfo_width()) // 2
            py = self.root.winfo_y() + (self.root.winfo_height() - win.winfo_height()) // 2
            win.geometry(f"+{px}+{py}")
        except Exception as e:
            import traceback as tb
            self._log(f"Update dialog error: {e}", "error")
            messagebox.showerror("Update Error", f"Failed to show update dialog:\n{e}")

    def _is_frozen(self):
        return getattr(sys, "frozen", False)

    def _download_and_install(self, zipball_url, latest_ver, binary_url, win):
        if self._is_frozen():
            self._download_binary(binary_url, latest_ver, win)
        else:
            self._download_source(zipball_url, latest_ver)

    def _download_source(self, url, ver):
        self._log(f"Downloading v{ver} source...", "file")
        self.status_text.set("Downloading update...")
        self.root.update_idletasks()

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AuditEngine/5.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
            z = zipfile.ZipFile(io.BytesIO(data))
            extract_dir = os.path.join(os.path.dirname(__file__), f"_update_{ver}")
            os.makedirs(extract_dir, exist_ok=True)
            z.extractall(extract_dir)
            members = os.listdir(extract_dir)
            if members:
                src = os.path.join(extract_dir, members[0])
                dst = os.path.dirname(__file__)
                for item in os.listdir(src):
                    s = os.path.join(src, item)
                    d = os.path.join(dst, item)
                    if os.path.isdir(s):
                        if os.path.exists(d):
                            shutil.rmtree(d)
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)
                shutil.rmtree(extract_dir)
            self._log("Source update installed. Restart to apply.", "success")
            if messagebox.askyesno("Restart Required",
                                   "Update installed. Restart now?"):
                self._restart_app()
        except Exception as e:
            self._log(f"Download failed: {e}", "error")
            messagebox.showerror("Update Failed", str(e))

    def _download_binary(self, url, ver, win):
        if not url:
            messagebox.showerror("Error", "No binary download URL available.")
            return
        win.destroy()
        self._log(f"Downloading binary v{ver}...", "file")
        self.status_text.set("Downloading binary update...")
        self.root.update_idletasks()

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AuditEngine/5.0"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
            dst = os.path.join(os.path.dirname(__file__), f"AuditEngine_{ver}.app.zip")
            with open(dst, "wb") as f:
                f.write(data)
            self._log(f"Downloaded: {dst}", "success")
            current_app = os.path.dirname(os.path.dirname(__file__))
            target = os.path.join(os.path.dirname(current_app), f"AuditEngine_{ver}.app")
            swap_script = os.path.join(os.path.dirname(__file__), "_swap.sh")
            with open(swap_script, "w") as f:
                f.write("#!/bin/bash\n")
                f.write("sleep 2\n")
                f.write(f'mv "{current_app}" "{current_app}.bak"\n')
                f.write(f'unzip -o "{dst}" -d "{os.path.dirname(target)}"\n')
                f.write(f'rm "{dst}"\n')
                f.write(f'open "{target}"\n')
            os.chmod(swap_script, 0o755)
            self._log("Binary downloaded. Swap script ready.", "success")
            if messagebox.askyesno("Restart Required",
                                   "Binary downloaded. Restart to install?"):
                self._restart_app(swap_script)
        except Exception as e:
            self._log(f"Download failed: {e}", "error")
            messagebox.showerror("Update Failed", str(e))

    def _restart_app(self, swap_script=None):
        self.cfg["window_geo"] = self.root.geometry()
        _save_config(self.cfg)
        self.root.destroy()
        if swap_script:
            subprocess.Popen(["/bin/bash", swap_script])
        else:
            python = sys.executable
            script = os.path.abspath(__file__)
            subprocess.Popen([python, script])

    def _cancel(self):
        self._cancel_event.set()
        self._log("Cancelling... Please wait for current operation to stop.", "warn")

    def _on_close(self):
        try:
            self.cfg["window_geo"] = self.root.geometry()
        except tk.TclError:
            pass
        self.cfg["idfc_type"] = self.idfc_audit_type.get()
        self.cfg["eq_format"] = self.eq_format.get()
        self.cfg["eq_mode"] = self.eq_mode.get()
        _save_config(self.cfg)
        self._cancel_event.set()
        self.root.destroy()

    def _set_buttons_state(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        for btn in [self.btn_idfc, self.btn_eq1, self.btn_eq2,
                     self.btn_browse, self.btn_out, self.btn_open_output, self.btn_clear_log,
                     self.btn_update]:
            btn.configure(state=state)

    def _update_progress(self, pct, msg=""):
        self.progress_var.set(pct)
        self.progress_pct_var.set(f"{int(pct)}%")
        if msg:
            self.status_text.set(msg)

    def _current_op(self, msg):
        self.current_op.set(msg)

    def _show_summary(self, title, lines):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(bg=self.COLORS["card"])
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text=title, font=("Segoe UI", 14, "bold"),
                 fg=self.COLORS["fg"], bg=self.COLORS["card"]).pack(pady=(16, 10))
        for line in lines:
            tk.Label(win, text=line, font=("Segoe UI", 10),
                     fg=self.COLORS["fg"], bg=self.COLORS["card"],
                     anchor="w").pack(padx=24, anchor="w")

        tk.Button(win, text="OK", font=("Segoe UI", 10, "bold"),
                  bg=self.COLORS["accent"], fg="#ffffff",
                  relief="flat", padx=32, pady=6, borderwidth=0,
                  activebackground=self.COLORS["accent_hover"],
                  command=win.destroy).pack(pady=(12, 16))

        win.update_idletasks()
        px = self.root.winfo_x() + (self.root.winfo_width() - win.winfo_width()) // 2
        py = self.root.winfo_y() + (self.root.winfo_height() - win.winfo_height()) // 2
        win.geometry(f"+{px}+{py}")

    def _run(self, mode):
        path = self.file_path.get().strip()
        if not path:
            messagebox.showwarning("No File", "Please select an Excel file first.")
            return
        if not os.path.isfile(path):
            messagebox.showerror("Error", "File not found.")
            return

        self._cancel_event.clear()
        self.progress_var.set(0)
        self.progress_pct_var.set("0%")
        self.current_op.set("")
        self.elapsed_text.set("")
        self.log_text.delete("1.0", tk.END)
        self.status_text.set("Running...")
        self.status_dot.configure(fg=self.COLORS["accent"])
        self._make_tooltip(self.status_dot, "Running")
        self._set_buttons_state(False)
        self._timer_start()

        mode_names = {"idfc": "IDFC", "equitas1": "Equitas Stage 1", "equitas2": "Equitas Stage 2"}
        self._log(f"Starting {mode_names.get(mode, mode)} processing...")

        t = threading.Thread(target=self._run_worker, args=(mode, path), daemon=True)
        t.start()

    def _run_worker(self, mode, path):
        error_occurred = False
        try:
            if mode == "idfc":
                self._process_idfc(path)
            elif mode == "equitas1":
                self._process_equitas1(path)
            elif mode == "equitas2":
                self._process_equitas2(path)
        except Exception as e:
            error_occurred = True
            self._log(f"ERROR: {e}", "error")
            self._log(traceback.format_exc(), "error")
            err_msg = str(e)
            self.root.after(0, lambda: messagebox.showerror("Error", err_msg))
        finally:
            was_cancelled = self._cancel_event.is_set()
            self.root.after(0, lambda: (
                self._set_buttons_state(True),
                self._current_op(""),
                self._timer_stop(keep_elapsed=True),
                None
            ))
            self.root.after(0, lambda ec=error_occurred, wc=was_cancelled: (
                self.status_dot.configure(
                    fg=self.COLORS["error"] if ec else
                    self.COLORS["success"] if not wc else
                    self.COLORS["warning"]
                ),
                self._make_tooltip(self.status_dot,
                    "Failed" if ec else
                    "Ready" if not wc else
                    "Cancelled"
                ),
                self.status_text.set(
                    "Failed" if ec else
                    "Complete" if not wc else
                    ""
                ),
                self.progress_pct_label.config(
                    text="FAIL" if ec else
                    "100%" if not wc else
                    ""
                ) if ec or not wc else None,
                self._update_progress(100, "Complete") if not ec and not wc else None,
                None
            ))

    def _process_idfc(self, path):
        self._current_op("Validating file...")
        valid, info = pdf_logic.validate_idfc_file(path)
        if not valid:
            self._log(f"Validation failed: {info}", "error")
            return

        out_dir = self.output_dir.get()
        os.makedirs(out_dir, exist_ok=True)
        data = pdf_logic.load_idfc_data(path)
        branches = pdf_logic.group_by_branch(data)
        total = len(branches)
        self._log(f"Loaded {total} branches from {os.path.basename(path)}")

        for i, (branch_code, branch_rows) in enumerate(branches.items(), 1):
            if self._cancel_event.is_set():
                self._log("Cancelled by user.", "warn")
                return

            branch_name = branch_rows[0].get("CurrentBranchName", branch_code) if branch_rows else branch_code
            state = branch_rows[0].get("State", "") if branch_rows else ""
            safe_name = f"{branch_code}_{branch_name}.pdf".replace(" ", "_").replace("/", "_")
            output_path = os.path.join(out_dir, safe_name)

            self._current_op(f"[{i}/{total}] Generating PDF: {branch_code}...")
            audit_type = self.idfc_audit_type.get()
            pdf_logic.generate_pdf(audit_type, branch_code, branch_name, state, branch_rows, output_path)
            self._log(f"[{i}/{total}] PDF: {safe_name}")
            self._update_progress(int(i / total * 100), f"Processing {branch_code}")

        self._log(f"Done. {total} PDFs saved to {out_dir}", "success")
        self._show_summary("IDFC Complete", [
            f"Branches processed: {total}",
            f"PDF reports saved: {total}",
            f"Output: {out_dir}",
        ])

    def _process_equitas1(self, path):
        self._current_op("Validating file...")
        valid, info = equitas_logic.validate_equitas_stage1_file(path)
        if not valid:
            self._log(f"Validation failed: {info}", "error")
            return

        out_dir = self.output_dir.get()
        os.makedirs(out_dir, exist_ok=True)
        self._log(f"Output: {out_dir}")

        def log_cb(msg):
            self._log(msg)

        def progress_cb(pct):
            self._update_progress(int(pct), f"Processing... {int(pct)}%")

        self._current_op("Building master dataframe...")
        result = equitas_logic.run_equitas_stage1(
            file_path=path,
            output_dir=out_dir,
            log_callback=log_cb,
            cancel_event=self._cancel_event,
            progress_callback=progress_cb,
        )
        if result:
            self._log(f"Stage 1 complete. Output: {result}", "success")
            self._show_summary("Equitas Stage 1 Complete", [
                f"Output: {os.path.basename(result)}" if os.path.isfile(result) else f"Output: {result}",
            ])
        else:
            self._log("Stage 1 cancelled or produced no output.", "warn")

    def _process_equitas2(self, path):
        self._current_op("Validating file...")
        valid, info = equitas_logic.validate_equitas_stage2_file(path)
        if not valid:
            self._log(f"Validation failed: {info}", "error")
            return

        out_dir = self.output_dir.get()
        os.makedirs(out_dir, exist_ok=True)
        self._log(f"Output: {out_dir}")

        def log_cb(msg):
            self._log(msg)

        def progress_cb(pct):
            self._update_progress(int(pct), f"Processing... {int(pct)}%")

        self._current_op("Consolidating accounts...")
        result = equitas_logic.run_equitas_stage2(
            file_path=path,
            output_dir=out_dir,
            log_callback=log_cb,
            cancel_event=self._cancel_event,
            progress_callback=progress_cb,
        )
        if result:
            self._log(f"Stage 2 complete. Output: {result}", "success")
            self._show_summary("Equitas Stage 2 Complete", [
                f"Consolidated file: {os.path.basename(result)}",
                f"Output: {out_dir}",
            ])
        else:
            self._log("Stage 2 cancelled or produced no output.", "warn")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = AuditEngineGUI()
    app.run()
