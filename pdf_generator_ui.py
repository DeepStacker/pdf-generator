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
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Audit Engine Elite v4.0")
        self.root.geometry("1200x900")
        self.root.configure(bg="#0F172A")
        
        self.active_tab = "PROCESS"
        self.log_queue = queue.Queue()
        
        self.setup_styles()
        self.setup_ui()
        self.root.after(100, self.check_log_queue)

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("Treeview", background="#1E293B", foreground="#F8FAFC", fieldbackground="#1E293B", rowheight=40, font=("Inter", 9))
        self.style.configure("Treeview.Heading", font=("Inter", 10, "bold"), background="#334155", foreground="#F8FAFC")
        self.style.map("Treeview", background=[('selected', '#2563EB')])

    def setup_ui(self):
        # Sidebar
        self.sidebar = tk.Frame(self.root, bg="#0F172A", width=260)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)
        
        tk.Label(self.sidebar, text="IDFC FIRST", font=("Inter", 20, "bold"), bg="#0F172A", fg="#FFFFFF", pady=40).pack()
        
        self.nav_btns = {}
        nav_items = [("🚀", "New Batch", "PROCESS"), ("📈", "Analytics", "STATS"), ("📂", "History", "HISTORY"), ("⚙️", "Settings", "SETTINGS")]
        for icon, label, tag in nav_items:
            self.nav_btns[tag] = self.create_nav_btn(f"{icon}  {label}", tag)

        tk.Label(self.sidebar, text="Enterprise v4.0.0", font=("Inter", 8), bg="#0F172A", fg="#475569").pack(side=tk.BOTTOM, pady=20)

        # Content Area
        self.content = tk.Frame(self.root, bg="#F8FAFC", padx=40, pady=40)
        self.content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.render_tab()

    def create_nav_btn(self, text, tag):
        bg = "#1E293B" if self.active_tab == tag else "#0F172A"
        btn = tk.Button(self.sidebar, text=text, font=("Inter", 11, "bold"), bg=bg, fg="#94A3B8", 
                        activebackground="#1E293B", activeforeground="#FFFFFF", relief="flat", anchor="w", 
                        padx=30, pady=18, cursor="hand2", command=lambda: self.switch_tab(tag))
        btn.pack(fill=tk.X)
        return btn

    def switch_tab(self, tag):
        self.active_tab = tag
        for t, b in self.nav_btns.items():
            b.config(bg="#1E293B" if self.active_tab == t else "#0F172A", fg="#FFFFFF" if self.active_tab == t else "#94A3B8")
        self.render_tab()

    def render_tab(self):
        for w in self.content.winfo_children(): w.destroy()
        
        if self.active_tab == "PROCESS":
            self.render_process()
        elif self.active_tab == "HISTORY":
            self.render_history()
        elif self.active_tab == "STATS":
            self.render_stats()
        elif self.active_tab == "SETTINGS":
            self.render_settings()

    def render_process(self):
        tk.Label(self.content, text="Dashboard", font=("Inter", 24, "bold"), bg="#F8FAFC", fg="#0F172A").pack(anchor="w")
        
        stats_frame = tk.Frame(self.content, bg="#F8FAFC")
        stats_frame.pack(fill=tk.X, pady=30)
        e, p = get_stats()
        self.create_stat_card(stats_frame, "Total Batches", str(e), "#0F172A", 0)
        self.create_stat_card(stats_frame, "Reports Built", str(p), "#2563EB", 1)
        self.create_stat_card(stats_frame, "System Health", "OPTIMAL", "#10B981", 2)

        card = tk.Frame(self.content, bg="#FFFFFF", padx=40, pady=40, highlightthickness=1, highlightbackground="#E2E8F0")
        card.pack(fill=tk.X)
        
        self.create_input(card, "Source Excel File", "file_var", self.browse_in, "BROWSE")
        self.lbl_info = tk.Label(card, text="Ready for new batch.", font=("Inter", 9), bg="#FFFFFF", fg="#64748B")
        self.lbl_info.pack(anchor="w", pady=(2, 20))

        saved_path = get_config("out_path", os.path.join(os.path.expanduser("~"), "Desktop"))
        self.create_input(card, "Output Destination", "folder_var", self.browse_out, "CHANGE")
        self.folder_var.set(saved_path)
        tk.Label(card, text=f"Target: {saved_path}", font=("Inter", 8), bg="#FFFFFF", fg="#64748B").pack(anchor="w", pady=(2, 20))

        # Config
        row = tk.Frame(card, bg="#FFFFFF", pady=10)
        row.pack(fill=tk.X)
        tk.Label(row, text="Audit Config:", font=("Inter", 10, "bold"), bg="#FFFFFF").pack(side=tk.LEFT)
        self.typ_var = tk.StringVar(value="POA")
        for t in ["POA", "TAF"]: tk.Radiobutton(row, text=t, variable=self.typ_var, value=t, bg="#FFFFFF", font=("Inter", 10)).pack(side=tk.LEFT, padx=15)
        
        self.auto_open = tk.BooleanVar(value=get_config("auto_open", "True")=="True")
        tk.Checkbutton(row, text="Auto-open folder", variable=self.auto_open, bg="#FFFFFF", font=("Inter", 9)).pack(side=tk.RIGHT)

        self.btn_run = tk.Button(card, text="EXECUTE ENGINE", font=("Inter", 13, "bold"), bg="#2563EB", fg="#FFFFFF", relief="flat", padx=50, pady=18, cursor="hand2", command=self.start_process)
        self.btn_run.pack(fill=tk.X, pady=(30, 0))

        # Log
        self.log_area = scrolledtext.ScrolledText(self.content, height=8, bg="#FFFFFF", borderwidth=0, font=("Menlo", 9), highlightthickness=1, highlightbackground="#E2E8F0")
        self.log_area.pack(fill=tk.BOTH, expand=True, pady=20)

    def render_stats(self):
        tk.Label(self.content, text="System Analytics", font=("Inter", 24, "bold"), bg="#F8FAFC", fg="#0F172A").pack(anchor="w", pady=(0, 30))
        types, trend = get_analytics()
        
        # Grid for Analytics
        grid = tk.Frame(self.content, bg="#F8FAFC")
        grid.pack(fill=tk.BOTH, expand=True)
        
        # Audit Type Card
        t_card = tk.Frame(grid, bg="#FFFFFF", padx=30, pady=30, highlightthickness=1, highlightbackground="#E2E8F0")
        t_card.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        tk.Label(t_card, text="AUDIT TYPE DISTRIBUTION", font=("Inter", 10, "bold"), bg="#FFFFFF", fg="#64748B").pack(anchor="w", pady=(0, 20))
        for t, c in types.items():
            r = tk.Frame(t_card, bg="#FFFFFF", pady=10)
            r.pack(fill=tk.X)
            tk.Label(r, text=t, font=("Inter", 11), bg="#FFFFFF").pack(side=tk.LEFT)
            tk.Label(r, text=str(c), font=("Inter", 11, "bold"), bg="#FFFFFF", fg="#2563EB").pack(side=tk.RIGHT)
            ttk.Progressbar(t_card, value=(c/sum(types.values()))*100 if sum(types.values())>0 else 0).pack(fill=tk.X)

        # Trend Card
        tr_card = tk.Frame(grid, bg="#FFFFFF", padx=30, pady=30, highlightthickness=1, highlightbackground="#E2E8F0")
        tr_card.grid(row=0, column=1, sticky="nsew", padx=(15, 0))
        tk.Label(tr_card, text="DAILY ACTIVITY TREND", font=("Inter", 10, "bold"), bg="#FFFFFF", fg="#64748B").pack(anchor="w", pady=(0, 20))
        for d, c in trend:
            r = tk.Frame(tr_card, bg="#FFFFFF", pady=8)
            r.pack(fill=tk.X)
            tk.Label(r, text=d, font=("Inter", 10), bg="#FFFFFF").pack(side=tk.LEFT)
            tk.Label(r, text=f"{c} Batches", font=("Inter", 10, "bold"), bg="#FFFFFF", fg="#059669").pack(side=tk.RIGHT)

        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)

    def render_history(self):
        tk.Label(self.content, text="Activity Log", font=("Inter", 24, "bold"), bg="#F8FAFC", fg="#0F172A").pack(anchor="w", pady=(0, 20))
        
        search_f = tk.Frame(self.content, bg="#F8FAFC")
        search_f.pack(fill=tk.X, pady=(0, 20))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh_history())
        tk.Entry(search_f, textvariable=self.search_var, font=("Inter", 11), bg="#FFFFFF", highlightthickness=1, highlightbackground="#E2E8F0", relief="flat").pack(fill=tk.X, ipady=10)
        
        h_card = tk.Frame(self.content, bg="#FFFFFF", highlightthickness=1, highlightbackground="#E2E8F0")
        h_card.pack(fill=tk.BOTH, expand=True)
        
        cols = ("Time", "Filename", "PDFs", "Type")
        self.tree = ttk.Treeview(h_card, columns=cols, show="headings", height=15)
        for c in cols: self.tree.heading(c, text=c)
        self.tree.column("Time", width=180)
        self.tree.column("Filename", width=400)
        self.tree.column("PDFs", width=100, anchor="center")
        self.tree.column("Type", width=100, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        self.refresh_history()
        
        btn_bar = tk.Frame(self.content, bg="#F8FAFC", pady=20)
        btn_bar.pack(fill=tk.X)
        tk.Button(btn_bar, text="Open Folder", bg="#2563EB", fg="#FFFFFF", font=("Inter", 10, "bold"), relief="flat", padx=30, pady=12, command=self.open_sel).pack(side=tk.LEFT)
        tk.Button(btn_bar, text="Export History to Excel", bg="#059669", fg="#FFFFFF", font=("Inter", 10, "bold"), relief="flat", padx=30, pady=12, command=self.export_history).pack(side=tk.RIGHT)

    def render_settings(self):
        tk.Label(self.content, text="Settings", font=("Inter", 24, "bold"), bg="#F8FAFC", fg="#0F172A").pack(anchor="w", pady=(0, 30))
        card = tk.Frame(self.content, bg="#FFFFFF", padx=40, pady=40, highlightthickness=1, highlightbackground="#E2E8F0")
        card.pack(fill=tk.X)
        tk.Label(card, text="Persistence: SQLite v3", font=("Inter", 10), bg="#FFFFFF", fg="#64748B").pack(anchor="w")
        tk.Label(card, text=f"DB: {DB_PATH}", font=("Inter", 9), bg="#FFFFFF", fg="#94A3B8").pack(anchor="w", pady=(0, 30))

    def create_stat_card(self, parent, title, val, color, col):
        card = tk.Frame(parent, bg="#FFFFFF", padx=30, pady=30, highlightthickness=1, highlightbackground="#E2E8F0")
        card.grid(row=0, column=col, sticky="nsew", padx=10)
        parent.grid_columnconfigure(col, weight=1)
        tk.Label(card, text=title.upper(), font=("Inter", 8, "bold"), bg="#FFFFFF", fg="#94A3B8").pack(anchor="w")
        tk.Label(card, text=val, font=("Inter", 20, "bold"), bg="#FFFFFF", fg=color).pack(anchor="w", pady=(10, 0))

    def create_input(self, parent, label, var_name, cmd, btn_txt):
        tk.Label(parent, text=label, font=("Inter", 10, "bold"), bg="#FFFFFF", fg="#1E293B").pack(anchor="w")
        row = tk.Frame(parent, bg="#FFFFFF")
        row.pack(fill=tk.X, pady=(10, 5))
        var = tk.StringVar()
        setattr(self, var_name, var)
        tk.Entry(row, textvariable=var, font=("Inter", 11), bg="#F8FAFC", relief="flat", highlightthickness=1, highlightbackground="#E2E8F0").pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=12, padx=(0, 20))
        tk.Button(row, text=btn_txt, font=("Inter", 9, "bold"), bg="#F1F5F9", relief="flat", padx=25, pady=12, command=cmd).pack(side=tk.LEFT)

    def log(self, msg): self.log_queue.put(msg)
    def check_log_queue(self):
        while not self.log_queue.empty():
            self.log_area.insert(tk.END, f"• {self.log_queue.get()}\n")
            self.log_area.see(tk.END)
        self.root.after(100, self.check_log_queue)

    def browse_in(self):
        f = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx *.xls")])
        if f: 
            self.file_var.set(f)
            self.lbl_info.config(text=f"Loaded: {os.path.basename(f)}", fg="#059669")
    def browse_out(self):
        f = filedialog.askdirectory()
        if f: 
            self.folder_var.set(f)
            set_config("out_path", f)

    def refresh_history(self):
        if self.active_tab == "HISTORY":
            for i in self.tree.get_children(): self.tree.delete(i)
            for h in get_recent_history(self.search_var.get()):
                self.tree.insert("", tk.END, values=(h[1], h[2], h[3], h[5]), tags=(h[4],))

    def open_sel(self):
        sel = self.tree.selection()
        if sel:
            path = self.tree.item(sel[0], "tags")[0]
            if os.path.exists(path):
                if sys.platform=="win32": os.startfile(path)
                else: os.system(f'open "{path}"')

    def export_history(self):
        f = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if f:
            data = get_recent_history(limit=1000)
            df = pd.DataFrame(data, columns=["ID", "Timestamp", "Filename", "PDFs", "Path", "Type"])
            df.to_excel(f, index=False)
            messagebox.showinfo("Export", "History exported successfully!")

    def start_process(self):
        inp, out, typ = self.file_var.get().strip(), self.folder_var.get().strip(), self.typ_var.get().strip()
        if not inp or not os.path.exists(inp): return messagebox.showerror("Error", "Select file.")
        self.btn_run.config(state=tk.DISABLED, text="PROCESSING BATCH...")
        set_config("auto_open", str(self.auto_open.get()))
        threading.Thread(target=self.worker, args=(inp, out, typ), daemon=True).start()

    def worker(self, inp, out_base, typ):
        try:
            excel_name = os.path.splitext(os.path.basename(inp))[0]
            out = os.path.join(out_base, f"{excel_name}_{int(time.time())}")
            os.makedirs(out, exist_ok=True)
            s, h, rows = read_excel_original(inp, self.log)
            groups = {}
            for r in rows:
                b = str(r.get("CurrentBranch", "UNKNOWN")).strip()
                groups.setdefault(b, []).append(r)
            count = 0
            for c, br in sorted(groups.items()):
                name, st = str(br[0].get("CurrentBranchName", "")), str(br[0].get("State", ""))
                safe = name.replace("/", "_").replace("\\", "_") if name else str(c)
                path = os.path.join(out, f"{safe}_{typ}.pdf")
                self.log(f"Building: {os.path.basename(path)}")
                generate_pdf_original(typ, c, name, st, br, path)
                count += 1
            # FIXED: Pass 'typ' to log_generation
            log_generation(excel_name, count, out, typ)
            self.log(f"COMPLETE: {count} PDFs built.")
            if self.auto_open.get():
                if sys.platform=="win32": os.startfile(out)
                else: os.system(f'open "{out}"')
            self.root.after(0, lambda: messagebox.showinfo("Done", f"Success! {count} PDFs generated."))
        except Exception as e:
            self.log(f"CRITICAL: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.root.after(0, lambda: self.btn_run.config(state=tk.NORMAL, text="EXECUTE ENGINE"))

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()