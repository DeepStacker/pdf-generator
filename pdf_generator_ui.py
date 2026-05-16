#!/usr/bin/env python3
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import threading
import os
import sys
import queue
import time
import sqlite3
import urllib.request
import openpyxl
import pandas as pd
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# =========================================================
# ASSET & DATABASE HANDLING
# =========================================================
def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

FONT_DIR = get_resource_path("fonts")
os.makedirs(FONT_DIR, exist_ok=True)

# Database Setup
DB_PATH = os.path.join(os.path.expanduser("~"), ".idfc_pdf_generator_v3.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
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
    conn.commit()
    conn.close()

def set_config(key, value):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def get_config(key, default=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else default

def log_generation(excel_name, pdf_count, output_path, audit_type):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO history (timestamp, excel_name, pdf_count, output_path, audit_type) VALUES (?, ?, ?, ?, ?)",
                   (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), excel_name, pdf_count, output_path, audit_type))
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), SUM(pdf_count) FROM history")
    res = cursor.fetchone()
    conn.close()
    return (res[0] or 0, res[1] or 0)

def get_analytics():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Audit Type Breakdown
    cursor.execute("SELECT audit_type, COUNT(*) FROM history GROUP BY audit_type")
    types = dict(cursor.fetchall())
    # Daily Trend
    cursor.execute("SELECT strftime('%Y-%m-%d', timestamp), COUNT(*) FROM history GROUP BY 1 ORDER BY 1 DESC LIMIT 7")
    trend = cursor.fetchall()
    conn.close()
    return types, trend

def get_recent_history(search="", limit=100):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if search:
        cursor.execute("SELECT id, timestamp, excel_name, pdf_count, output_path, audit_type FROM history WHERE excel_name LIKE ? ORDER BY id DESC LIMIT ?", (f"%{search}%", limit))
    else:
        cursor.execute("SELECT id, timestamp, excel_name, pdf_count, output_path, audit_type FROM history ORDER BY id DESC LIMIT ?", (limit,))
    res = cursor.fetchall()
    conn.close()
    return res

init_db()

# Font Download Logic
CALIBRI_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/carlito/Carlito-Regular.ttf"
BOLD_URL = "https://raw.githubusercontent.com/googlefonts/arimo/main/fonts/ttf/Arimo-Bold.ttf"
reg_path = os.path.join(FONT_DIR, "Carlito-Regular.ttf")
bold_path = os.path.join(FONT_DIR, "Arimo-Bold.ttf")

def download_font(url, path):
    if not os.path.exists(path):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as r, open(path, 'wb') as f:
                f.write(r.read())
        except: pass

download_font(CALIBRI_URL, reg_path)
download_font(BOLD_URL, bold_path)

try:
    pdfmetrics.registerFont(TTFont('Carlito', reg_path))
    pdfmetrics.registerFont(TTFont('ArimoBold', bold_path))
    FONT_REG, FONT_BLD = 'Carlito', 'ArimoBold'
except:
    FONT_REG, FONT_BLD = 'Helvetica', 'Helvetica-Bold'

REQUIRED_COLUMNS = ["Prospectno", "CUID", "Tare Weight", "State", "CurrentBranch", "CurrentBranchName"]

# =========================================================
# CORE LOGIC (UNCHANGED PDF DESIGN)
# =========================================================
def format_tare_weight(val):
    if pd.isna(val) or val == "" or val is None: return ""
    try:
        fval = float(val)
        return str(int(fval)) if fval == int(fval) else str(fval)
    except: return str(val)

def read_excel_original(excel_path, log_callback=print):
    log_callback(f"Reading Excel: {os.path.basename(excel_path)}")
    wb = openpyxl.load_workbook(excel_path, data_only=True, read_only=True)
    required_lower = [c.lower() for c in REQUIRED_COLUMNS]
    target_sheet = None
    for sname in wb.sheetnames:
        ws = wb[sname]
        try:
            h_row = [str(cell.value).strip().replace("\n", "") if cell.value else "" for cell in next(ws.iter_rows(min_row=1, max_row=1))]
            if all(r in [h.lower() for h in h_row] for r in required_lower):
                target_sheet = sname
                break
        except: continue
    if not target_sheet: raise Exception("No valid sheet found.")
    ws = wb[target_sheet]
    headers = [str(cell.value).strip().replace("\n", "") if cell.value else "" for cell in next(ws.iter_rows(min_row=1, max_row=1))]
    rows = []
    for row in ws.iter_rows(min_row=2, values_only=False):
        row_data, all_none = {}, True
        for i, cell in enumerate(row):
            if i < len(headers) and headers[i]:
                val = cell.value
                if val is not None: all_none = False
                if headers[i] in ("Prospectno", "CUID"):
                    row_data[headers[i]] = str(val).strip() if val is not None else ""
                else: row_data[headers[i]] = val
        if not all_none: rows.append(row_data)
    return target_sheet, headers, rows

def generate_pdf_original(audit_type, branch_code, branch_name, state, rows, output_path):
    if not rows: return
    PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)
    doc = SimpleDocTemplate(output_path, pagesize=(PAGE_WIDTH, PAGE_HEIGHT), leftMargin=50.2, rightMargin=50.2, topMargin=48.0, bottomMargin=15)
    cw = [22.2, 101.1, 118.5, 60.3, 67.2, 125.0, 247.3]
    style_hdr = ParagraphStyle("ColHdr", fontName=FONT_BLD, fontSize=9, alignment=TA_CENTER, leading=10)
    table_data = [
        ["Audit Type :", "", str(audit_type), "", "Branch Name :", "", str(branch_name)],
        ["Branch Code :", "", str(branch_code), "", "State :", "", str(state)],
        [Paragraph("Sr<br/>No", style_hdr), Paragraph("Prospectno", style_hdr), Paragraph("CUID", style_hdr), 
         Paragraph("Tare Weight<br/>as per Bank", style_hdr), Paragraph("<nobr>Tare Weight as</nobr><br/>per Audit", style_hdr), 
         Paragraph("<nobr>Purity Check - 18K and</nobr><br/><nobr>above 18K or Below 18K</nobr>", style_hdr), Paragraph("Remarks", style_hdr)]
    ]
    for idx, row in enumerate(rows, 1):
        table_data.append([str(idx), str(row.get("Prospectno", "")), str(row.get("CUID", "")), format_tare_weight(row.get("Tare Weight", "")), "", "", ""])
    row_heights = [12.2, 14.2, 22.5] + [30.5] * (len(table_data) - 3)
    table = Table(table_data, colWidths=cw, rowHeights=row_heights, repeatRows=3)
    table.setStyle(TableStyle([
        ("SPAN", (0, 0), (1, 0)), ("SPAN", (4, 0), (5, 0)), ("SPAN", (0, 1), (1, 1)), ("SPAN", (4, 1), (5, 1)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 1), FONT_BLD), ("FONTSIZE", (0, 0), (-1, 1), 9),
        ("FONTNAME", (0, 3), (-1, -1), FONT_REG), ("FONTSIZE", (0, 3), (-1, -1), 9),
        ("FONTNAME", (0, 3), (0, -1), FONT_BLD),
        ("BACKGROUND", (0, 2), (3, 2), colors.HexColor("#FFFF00")),
        ("BACKGROUND", (4, 2), (6, 2), colors.HexColor("#4985E8")),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0), ("LEFTPADDING", (0, 0), (-1, -1), 1), ("RIGHTPADDING", (0, 0), (-1, -1), 1),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    doc.build([table])

# =========================================================
# APP - ANALYTICS & PROFESSIONAL SUITE
# =========================================================
# =========================================================
# APP - ANALYTICS & PROFESSIONAL SUITE
# =========================================================
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Audit Engine Elite v4.1")
        self.root.geometry("1200(900")
        self.root.configure(bg="#0F172A")
        
        # Performance optimization: handle high DPI
        try: self.root.tk.call('tk', 'scaling', 1.5)
        except: pass

        self.active_tab = "PROCESS"
        self.log_queue = queue.Queue()
        
        self.setup_styles()
        self.setup_ui()
        self.root.after(100, self.check_log_queue)

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        # Dark Mode Treeview
        self.style.configure("Treeview", 
                           background="#1E293B", 
                           foreground="#F8FAFC", 
                           fieldbackground="#1E293B", 
                           rowheight=45, 
                           font=("Inter", 10))
        self.style.configure("Treeview.Heading", 
                           font=("Inter", 11, "bold"), 
                           background="#334155", 
                           foreground="#F8FAFC",
                           relief="flat")
        self.style.map("Treeview", background=[('selected', '#2563EB')])

    def setup_ui(self):
        # Main Layout
        self.main_container = tk.Frame(self.root, bg="#0F172A")
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # Sidebar
        self.sidebar = tk.Frame(self.main_container, bg="#0F172A", width=280)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)
        
        # Logo Area
        logo_frame = tk.Frame(self.sidebar, bg="#0F172A", pady=50)
        logo_frame.pack(fill=tk.X)
        tk.Label(logo_frame, text="IDFC FIRST", font=("Inter", 24, "bold"), bg="#0F172A", fg="#FFFFFF").pack()
        tk.Label(logo_frame, text="AUDIT ENGINE ELITE", font=("Inter", 9, "bold"), bg="#0F172A", fg="#2563EB", pady=5).pack()
        
        # Navigation
        self.nav_btns = {}
        nav_items = [
            ("rocket", "New Batch", "PROCESS", "🚀"), 
            ("chart", "Analytics", "STATS", "📈"), 
            ("folder", "History", "HISTORY", "📂"), 
            ("settings", "Settings", "SETTINGS", "⚙️")
        ]
        
        nav_container = tk.Frame(self.sidebar, bg="#0F172A")
        nav_container.pack(fill=tk.X, expand=True, anchor="n")

        for _, label, tag, icon in nav_items:
            self.nav_btns[tag] = self.create_nav_btn(f"{icon}  {label}", tag, nav_container)

        # Footer
        footer = tk.Frame(self.sidebar, bg="#0F172A", pady=30)
        footer.pack(side=tk.BOTTOM, fill=tk.X)
        tk.Label(footer, text="v4.1.0 Enterprise Edition", font=("Inter", 8), bg="#0F172A", fg="#475569").pack()
        tk.Label(footer, text="© 2026 DeepMind Advanced", font=("Inter", 7), bg="#0F172A", fg="#334155").pack()

        # Content Area (Right Side)
        self.content_container = tk.Frame(self.main_container, bg="#F8FAFC")
        self.content_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Shadow Effect for sidebar
        tk.Frame(self.main_container, bg="#E2E8F0", width=1).pack(side=tk.LEFT, fill=tk.Y)

        self.render_tab()

    def create_nav_btn(self, text, tag, parent):
        btn = tk.Button(parent, text=text, font=("Inter", 12, "bold"), 
                        bg="#0F172A", fg="#94A3B8", 
                        activebackground="#1E293B", activeforeground="#FFFFFF", 
                        relief="flat", anchor="w", padx=40, pady=22, 
                        cursor="hand2", borderwidth=0,
                        command=lambda: self.switch_tab(tag))
        btn.pack(fill=tk.X)
        
        # Hover effect
        btn.bind("<Enter>", lambda e, b=btn: self.on_nav_hover(b, True))
        btn.bind("<Leave>", lambda e, b=btn: self.on_nav_hover(b, False))
        
        return btn

    def on_nav_hover(self, btn, is_hover):
        if btn["text"].split()[-1].upper() != self.active_tab:
            btn.config(bg="#1E293B" if is_hover else "#0F172A", fg="#F8FAFC" if is_hover else "#94A3B8")

    def switch_tab(self, tag):
        self.active_tab = tag
        for t, b in self.nav_btns.items():
            is_active = (self.active_tab == t)
            b.config(bg="#1E293B" if is_active else "#0F172A", 
                     fg="#FFFFFF" if is_active else "#94A3B8")
        self.render_tab()

    def render_tab(self):
        for w in self.content_container.winfo_children(): w.destroy()
        
        self.content = tk.Frame(self.content_container, bg="#F8FAFC", padx=50, pady=50)
        self.content.pack(fill=tk.BOTH, expand=True)

        if self.active_tab == "PROCESS":
            self.render_process()
        elif self.active_tab == "HISTORY":
            self.render_history()
        elif self.active_tab == "STATS":
            self.render_stats()
        elif self.active_tab == "SETTINGS":
            self.render_settings()

    def render_process(self):
        header = tk.Frame(self.content, bg="#F8FAFC")
        header.pack(fill=tk.X)
        tk.Label(header, text="Engine Dashboard", font=("Inter", 28, "bold"), bg="#F8FAFC", fg="#0F172A").pack(side=tk.LEFT)
        
        # Top Stats
        stats_frame = tk.Frame(self.content, bg="#F8FAFC")
        stats_frame.pack(fill=tk.X, pady=40)
        e, p = get_stats()
        self.create_stat_card(stats_frame, "Total Sessions", str(e), "#0F172A", 0)
        self.create_stat_card(stats_frame, "PDF Reports", str(p), "#2563EB", 1)
        self.create_stat_card(stats_frame, "Health Status", "SECURE", "#10B981", 2)

        # Control Panel
        panel = tk.Frame(self.content, bg="#FFFFFF", padx=45, pady=45, highlightthickness=1, highlightbackground="#E2E8F0")
        panel.pack(fill=tk.X)
        
        # Section 1: File Selection
        self.create_input(panel, "Source Master Excel", "file_var", self.browse_in, "BROWSE FILE")
        self.lbl_info = tk.Label(panel, text="Upload an IDFC Master file to begin.", font=("Inter", 10), bg="#FFFFFF", fg="#64748B")
        self.lbl_info.pack(anchor="w", pady=(5, 30))

        # Section 2: Audit Type
        tk.Label(panel, text="Select Audit Type", font=("Inter", 11, "bold"), bg="#FFFFFF", fg="#1E293B").pack(anchor="w")
        typ_row = tk.Frame(panel, bg="#FFFFFF", pady=15)
        typ_row.pack(fill=tk.X)
        self.typ_var = tk.StringVar(value="POA")
        for t in ["POA", "TAF"]:
            rb = tk.Radiobutton(typ_row, text=t, variable=self.typ_var, value=t, 
                                bg="#FFFFFF", font=("Inter", 11), selectcolor="#FFFFFF",
                                activebackground="#FFFFFF", cursor="hand2")
            rb.pack(side=tk.LEFT, padx=(0, 40))

        # Section 3: Output Config
        tk.Label(panel, text="Output Directory", font=("Inter", 11, "bold"), bg="#FFFFFF", fg="#1E293B", pady=(20,0)).pack(anchor="w")
        saved_path = get_config("out_path", os.path.join(os.path.expanduser("~"), "Desktop"))
        self.create_input(panel, "", "folder_var", self.browse_out, "CHANGE LOCATION")
        self.folder_var.set(saved_path)
        
        row_opt = tk.Frame(panel, bg="#FFFFFF", pady=20)
        row_opt.pack(fill=tk.X)
        self.auto_open = tk.BooleanVar(value=get_config("auto_open", "True")=="True")
        tk.Checkbutton(row_opt, text="Auto-open destination after build", variable=self.auto_open, 
                       bg="#FFFFFF", font=("Inter", 10), activebackground="#FFFFFF").pack(side=tk.LEFT)

        # Run Button
        self.btn_run = tk.Button(panel, text="START GENERATION ENGINE", font=("Inter", 14, "bold"), 
                                 bg="#2563EB", fg="#FFFFFF", relief="flat", padx=50, pady=22, 
                                 cursor="hand2", activebackground="#1D4ED8",
                                 command=self.start_process)
        self.btn_run.pack(fill=tk.X, pady=(30, 0))

        # Real-time Console
        tk.Label(self.content, text="ENGINE CONSOLE", font=("Inter", 9, "bold"), bg="#F8FAFC", fg="#94A3B8").pack(anchor="w", pady=(40, 5))
        self.log_area = scrolledtext.ScrolledText(self.content, height=10, bg="#1E293B", fg="#10B981", 
                                                borderwidth=0, font=("Menlo", 10), padx=20, pady=20,
                                                insertbackground="#FFFFFF")
        self.log_area.pack(fill=tk.BOTH, expand=True)

    def render_stats(self):
        header = tk.Frame(self.content, bg="#F8FAFC")
        header.pack(fill=tk.X, pady=(0, 40))
        tk.Label(header, text="Insight Analytics", font=("Inter", 28, "bold"), bg="#F8FAFC", fg="#0F172A").pack(side=tk.LEFT)
        tk.Button(header, text="↻ Refresh", font=("Inter", 10), bg="#F1F5F9", relief="flat", command=self.render_stats).pack(side=tk.RIGHT)

        types, trend = get_analytics()
        
        grid = tk.Frame(self.content, bg="#F8FAFC")
        grid.pack(fill=tk.BOTH, expand=True)
        
        # Distribution Card
        dist_card = tk.Frame(grid, bg="#FFFFFF", padx=40, pady=40, highlightthickness=1, highlightbackground="#E2E8F0")
        dist_card.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        tk.Label(dist_card, text="AUDIT TYPE SPLIT", font=("Inter", 11, "bold"), bg="#FFFFFF", fg="#64748B").pack(anchor="w", pady=(0, 30))
        
        total_batches = sum(types.values())
        for t in ["POA", "TAF"]:
            count = types.get(t, 0)
            pct = (count / total_batches * 100) if total_batches > 0 else 0
            
            row = tk.Frame(dist_card, bg="#FFFFFF", pady=15)
            row.pack(fill=tk.X)
            tk.Label(row, text=t, font=("Inter", 12), bg="#FFFFFF").pack(side=tk.LEFT)
            tk.Label(row, text=f"{count} ({pct:.1f}%)", font=("Inter", 12, "bold"), bg="#FFFFFF", fg="#2563EB").pack(side=tk.RIGHT)
            
            p = ttk.Progressbar(dist_card, length=200, mode="determinate")
            p.pack(fill=tk.X)
            p['value'] = pct

        # Activity Card
        trend_card = tk.Frame(grid, bg="#FFFFFF", padx=40, pady=40, highlightthickness=1, highlightbackground="#E2E8F0")
        trend_card.grid(row=0, column=1, sticky="nsew")
        tk.Label(trend_card, text="RECENT ACTIVITY (7 DAYS)", font=("Inter", 11, "bold"), bg="#FFFFFF", fg="#64748B").pack(anchor="w", pady=(0, 30))
        
        if not trend:
            tk.Label(trend_card, text="No activity data available yet.", font=("Inter", 11), bg="#FFFFFF", fg="#94A3B8").pack(pady=50)
        else:
            for d, c in trend:
                r = tk.Frame(trend_card, bg="#FFFFFF", pady=10)
                r.pack(fill=tk.X)
                tk.Label(r, text=d, font=("Inter", 11), bg="#FFFFFF").pack(side=tk.LEFT)
                tk.Label(r, text=f"{c} Batches", font=("Inter", 11, "bold"), bg="#FFFFFF", fg="#059669").pack(side=tk.RIGHT)
                tk.Frame(trend_card, bg="#F1F5F9", height=1).pack(fill=tk.X)

        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)

    def render_history(self):
        header = tk.Frame(self.content, bg="#F8FAFC")
        header.pack(fill=tk.X, pady=(0, 30))
        tk.Label(header, text="Generation Logs", font=("Inter", 28, "bold"), bg="#F8FAFC", fg="#0F172A").pack(side=tk.LEFT)
        
        search_f = tk.Frame(self.content, bg="#F8FAFC")
        search_f.pack(fill=tk.X, pady=(0, 25))
        
        tk.Label(search_f, text="Search Filename:", font=("Inter", 10, "bold"), bg="#F8FAFC", fg="#64748B").pack(anchor="w", pady=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh_history())
        search_entry = tk.Entry(search_f, textvariable=self.search_var, font=("Inter", 12), bg="#FFFFFF", highlightthickness=1, highlightbackground="#E2E8F0", relief="flat")
        search_entry.pack(fill=tk.X, ipady=12)

        # Table Card
        table_container = tk.Frame(self.content, bg="#FFFFFF", highlightthickness=1, highlightbackground="#E2E8F0")
        table_container.pack(fill=tk.BOTH, expand=True)
        
        cols = ("Time", "Filename", "PDF Count", "Type")
        self.tree = ttk.Treeview(table_container, columns=cols, show="headings", height=15)
        for c in cols: 
            self.tree.heading(c, text=c.upper(), anchor="center")
            self.tree.column(c, anchor="center")
        
        self.tree.column("Time", width=200)
        self.tree.column("Filename", width=450, anchor="w")
        self.tree.column("PDF Count", width=120)
        self.tree.column("Type", width=120)
        
        # Scrollbar
        sb = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.refresh_history()
        
        # Actions
        btn_bar = tk.Frame(self.content, bg="#F8FAFC", pady=30)
        btn_bar.pack(fill=tk.X)
        tk.Button(btn_bar, text="📂 Open Selected Batch Folder", bg="#2563EB", fg="#FFFFFF", 
                  font=("Inter", 11, "bold"), relief="flat", padx=35, pady=15, 
                  cursor="hand2", command=self.open_sel).pack(side=tk.LEFT)
        
        tk.Button(btn_bar, text="📑 Export All to Excel", bg="#059669", fg="#FFFFFF", 
                  font=("Inter", 11, "bold"), relief="flat", padx=35, pady=15, 
                  cursor="hand2", command=self.export_history).pack(side=tk.RIGHT)

    def render_settings(self):
        tk.Label(self.content, text="System Settings", font=("Inter", 28, "bold"), bg="#F8FAFC", fg="#0F172A").pack(anchor="w", pady=(0, 40))
        
        card = tk.Frame(self.content, bg="#FFFFFF", padx=50, pady=50, highlightthickness=1, highlightbackground="#E2E8F0")
        card.pack(fill=tk.X)
        
        tk.Label(card, text="DATABASE MANAGEMENT", font=("Inter", 11, "bold"), bg="#FFFFFF", fg="#64748B").pack(anchor="w", pady=(0, 20))
        tk.Label(card, text=f"Storage Engine: SQLite v3", font=("Inter", 11), bg="#FFFFFF", fg="#1E293B").pack(anchor="w")
        tk.Label(card, text=f"Location: {DB_PATH}", font=("Inter", 10), bg="#FFFFFF", fg="#94A3B8").pack(anchor="w", pady=(5, 30))
        
        tk.Button(card, text="🗑 CLEAR HISTORY DATABASE", font=("Inter", 10, "bold"), bg="#F1F5F9", fg="#E11D48", 
                  relief="flat", padx=30, pady=15, cursor="hand2", command=self.clear_history).pack(anchor="w")
        
        tk.Label(card, text="Caution: This will permanently delete all records and analytics.", font=("Inter", 9), bg="#FFFFFF", fg="#94A3B8", pady=10).pack(anchor="w")

    def clear_history(self):
        if messagebox.askyesno("Confirm Clear", "Are you sure you want to delete all history records? This cannot be undone."):
            conn = sqlite3.connect(DB_PATH)
            conn.execute("DELETE FROM history")
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "History cleared successfully.")
            self.render_tab()

    def create_stat_card(self, parent, title, val, color, col):
        card = tk.Frame(parent, bg="#FFFFFF", padx=35, pady=35, highlightthickness=1, highlightbackground="#E2E8F0")
        card.grid(row=0, column=col, sticky="nsew", padx=10)
        parent.grid_columnconfigure(col, weight=1)
        tk.Label(card, text=title.upper(), font=("Inter", 9, "bold"), bg="#FFFFFF", fg="#94A3B8").pack(anchor="w")
        tk.Label(card, text=val, font=("Inter", 24, "bold"), bg="#FFFFFF", fg=color).pack(anchor="w", pady=(15, 0))

    def create_input(self, parent, label, var_name, cmd, btn_txt):
        if label: tk.Label(parent, text=label, font=("Inter", 11, "bold"), bg="#FFFFFF", fg="#1E293B").pack(anchor="w")
        row = tk.Frame(parent, bg="#FFFFFF")
        row.pack(fill=tk.X, pady=(12, 5))
        var = tk.StringVar()
        setattr(self, var_name, var)
        tk.Entry(row, textvariable=var, font=("Inter", 12), bg="#F8FAFC", relief="flat", highlightthickness=1, highlightbackground="#E2E8F0").pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=15, padx=(0, 25))
        tk.Button(row, text=btn_txt, font=("Inter", 10, "bold"), bg="#F1F5F9", relief="flat", padx=30, pady=15, cursor="hand2", command=cmd).pack(side=tk.LEFT)

    def log(self, msg): self.log_queue.put(msg)
    def check_log_queue(self):
        while not self.log_queue.empty():
            self.log_area.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] » {self.log_queue.get()}\n")
            self.log_area.see(tk.END)
        self.root.after(100, self.check_log_queue)

    def browse_in(self):
        f = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx *.xls")])
        if f: 
            self.file_var.set(f)
            self.lbl_info.config(text=f"Loaded Strategy: {os.path.basename(f)}", fg="#059669")
    def browse_out(self):
        f = filedialog.askdirectory()
        if f: 
            self.folder_var.set(f)
            set_config("out_path", f)

    def refresh_history(self):
        if hasattr(self, 'tree') and self.active_tab == "HISTORY":
            for i in self.tree.get_children(): self.tree.delete(i)
            records = get_recent_history(self.search_var.get())
            for h in records:
                # h = (id, timestamp, excel_name, pdf_count, output_path, audit_type)
                self.tree.insert("", tk.END, values=(h[1], h[2], h[3], h[5]), tags=(h[4],))

    def open_sel(self):
        sel = self.tree.selection()
        if sel:
            path = self.tree.item(sel[0], "tags")[0]
            if os.path.exists(path):
                if sys.platform=="win32": os.startfile(path)
                else: os.system(f'open "{path}"')
            else:
                messagebox.showerror("Error", "Folder no longer exists.")

    def export_history(self):
        f = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if f:
            data = get_recent_history(limit=1000)
            df = pd.DataFrame(data, columns=["ID", "Timestamp", "Filename", "PDFs", "Path", "AuditType"])
            df.to_excel(f, index=False)
            messagebox.showinfo("Export", "Elite history data exported successfully!")

    def start_process(self):
        inp, out, typ = self.file_var.get().strip(), self.folder_var.get().strip(), self.typ_var.get().strip()
        if not inp or not os.path.exists(inp): 
            return messagebox.showerror("System Error", "Please select a valid source Excel file.")
        
        self.btn_run.config(state=tk.DISABLED, text="ENGINE RUNNING - PLEASE WAIT...")
        set_config("auto_open", str(self.auto_open.get()))
        
        # Clear log
        self.log_area.delete(1.0, tk.END)
        self.log("Engine Initialized. Starting thread safety checks...")
        
        threading.Thread(target=self.worker, args=(inp, out, typ), daemon=True).start()

    def worker(self, inp, out_base, typ):
        try:
            excel_name = os.path.splitext(os.path.basename(inp))[0]
            # Create a unique subfolder
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            out = os.path.join(out_base, f"{excel_name}_{timestamp_str}")
            os.makedirs(out, exist_ok=True)
            
            self.log(f"Loading Master: {excel_name}")
            s, h, rows = read_excel_original(inp, self.log)
            
            # Group by Branch
            groups = {}
            for r in rows:
                b = str(r.get("CurrentBranch", "UNKNOWN")).strip()
                groups.setdefault(b, []).append(r)
            
            self.log(f"Detected {len(groups)} unique branches.")
            count = 0
            
            for c, br in sorted(groups.items()):
                name = str(br[0].get("CurrentBranchName", "Unnamed Branch"))
                st = str(br[0].get("State", ""))
                
                # Sanitize name
                safe_name = "".join(x for x in name if x.isalnum() or x in " -_").strip()
                path = os.path.join(out, f"{safe_name}_{typ}.pdf")
                
                self.log(f"Building Report: {safe_name}")
                generate_pdf_original(typ, c, name, st, br, path)
                count += 1
            
            # Log to DB with specific type
            log_generation(excel_name, count, out, typ)
            
            self.log("==========================================")
            self.log(f"SUCCESS: {count} Reports generated successfully.")
            self.log(f"Target: {out}")
            self.log("==========================================")
            
            if self.auto_open.get():
                if sys.platform=="win32": os.startfile(out)
                else: os.system(f'open "{out}"')
                
            self.root.after(0, lambda: messagebox.showinfo("Build Success", f"All {count} PDF reports have been successfully generated in the target folder."))
        
        except Exception as e:
            self.log(f"ENGINE FAILURE: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Engine Failure", f"A critical error occurred:\n{str(e)}"))
        
        finally:
            self.root.after(0, lambda: self.btn_run.config(state=tk.NORMAL, text="START GENERATION ENGINE"))
            self.root.after(0, self.refresh_history) # Proactively refresh

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()