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
DB_PATH = os.path.join(os.path.expanduser("~"), ".idfc_pdf_generator.db")

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
    conn.commit()
    conn.close()

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

def get_recent_history(limit=50):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, excel_name, pdf_count, output_path FROM history ORDER BY id DESC LIMIT ?", (limit,))
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
# APP - ULTIMATE MODERN ENTERPRISE UI
# =========================================================
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("IDFC First Bank Audit Engine v2.0")
        self.root.geometry("1000x800")
        self.root.configure(bg="#F1F5F9")
        
        self.active_tab = "PROCESS"
        self.log_queue = queue.Queue()
        
        # Styles
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("Treeview", background="#FFFFFF", fieldbackground="#FFFFFF", rowheight=30)
        self.style.map("Treeview", background=[('selected', '#1E40AF')])
        
        self.setup_ui()
        self.update_stats_labels()
        self.root.after(100, self.check_log_queue)

    def setup_ui(self):
        # Sidebar
        self.sidebar = tk.Frame(self.root, bg="#1E293B", width=220)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)
        
        tk.Label(self.sidebar, text="IDFC FIRST", font=("Inter", 16, "bold"), bg="#1E293B", fg="#FFFFFF", pady=30).pack()
        
        self.btn_proc = self.create_nav_item("Dashboard & Process", "PROCESS")
        self.btn_hist = self.create_nav_item("Audit History", "HISTORY")
        self.btn_about = self.create_nav_item("System Info", "ABOUT")
        
        tk.Label(self.sidebar, text="Engine v2.0.0", font=("Inter", 8), bg="#1E293B", fg="#94A3B8").pack(side=tk.BOTTOM, pady=20)

        # Main Content Area
        self.main_area = tk.Frame(self.root, bg="#F1F5F9", padx=40, pady=30)
        self.main_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.render_content()

    def create_nav_item(self, text, tag):
        bg = "#334155" if self.active_tab == tag else "#1E293B"
        btn = tk.Button(self.sidebar, text=f"  {text}", font=("Inter", 10), bg=bg, fg="#CBD5E1", 
                        activebackground="#475569", activeforeground="#FFFFFF", relief="flat", anchor="w", 
                        padx=20, pady=12, cursor="hand2", command=lambda: self.switch_tab(tag))
        btn.pack(fill=tk.X, pady=2)
        return btn

    def switch_tab(self, tag):
        self.active_tab = tag
        # Reset colors
        for b, t in [(self.btn_proc, "PROCESS"), (self.btn_hist, "HISTORY"), (self.btn_about, "ABOUT")]:
            b.config(bg="#334155" if self.active_tab == t else "#1E293B")
        self.render_content()

    def render_content(self):
        for widget in self.main_area.winfo_children(): widget.destroy()
        
        if self.active_tab == "PROCESS":
            self.render_process_tab()
        elif self.active_tab == "HISTORY":
            self.render_history_tab()
        elif self.active_tab == "ABOUT":
            self.render_about_tab()

    def render_process_tab(self):
        tk.Label(self.main_area, text="System Dashboard", font=("Inter", 18, "bold"), bg="#F1F5F9", fg="#0F172A").pack(anchor="w")
        
        # Stats Row
        stats_frame = tk.Frame(self.main_area, bg="#F1F5F9")
        stats_frame.pack(fill=tk.X, pady=25)
        e, p = get_stats()
        self.card_excels = self.create_stat_card(stats_frame, "Total Excels", str(e), "#1E40AF", 0)
        self.card_pdfs = self.create_stat_card(stats_frame, "Total PDFs", str(p), "#10B981", 1)
        self.card_status = self.create_stat_card(stats_frame, "Engine Status", "STANDBY", "#64748B", 2)

        # Action Area
        action_card = tk.Frame(self.main_area, bg="#FFFFFF", padx=30, pady=30, highlightthickness=1, highlightbackground="#E2E8F0")
        action_card.pack(fill=tk.X)
        
        tk.Label(action_card, text="Quick Batch Process", font=("Inter", 11, "bold"), bg="#FFFFFF", fg="#1E293B").pack(anchor="w", pady=(0, 20))
        
        self.create_input_field(action_card, "Select Excel Source File", "file_var", self.browse_in, "BROWSE")
        self.lbl_file_info = tk.Label(action_card, text="Waiting for file...", font=("Inter", 9), bg="#FFFFFF", fg="#64748B")
        self.lbl_file_info.pack(anchor="w", pady=(0, 15))

        self.create_input_field(action_card, "Select Output Directory", "folder_var", self.browse_out, "SELECT")
        self.folder_var.set(os.path.join(os.path.expanduser("~"), "Desktop"))
        tk.Label(action_card, text=f"Target: {self.folder_var.get()}", font=("Inter", 8), bg="#FFFFFF", fg="#64748B").pack(anchor="w", pady=(0, 20))

        # Config Area
        cfg_row = tk.Frame(action_card, bg="#FFFFFF")
        cfg_row.pack(fill=tk.X, pady=10)
        tk.Label(cfg_row, text="Audit Type:", font=("Inter", 10, "bold"), bg="#FFFFFF").pack(side=tk.LEFT)
        self.typ_var = tk.StringVar(value="POA")
        for t in ["POA", "TAF"]:
            tk.Radiobutton(cfg_row, text=t, variable=self.typ_var, value=t, bg="#FFFFFF").pack(side=tk.LEFT, padx=15)

        self.btn_run = tk.Button(action_card, text="START ENGINE", font=("Inter", 12, "bold"), bg="#1E40AF", fg="#FFFFFF", relief="flat", padx=40, pady=12, cursor="hand2", command=self.start_process)
        self.btn_run.pack(fill=tk.X, pady=(20, 0))

        # Log Area
        tk.Label(self.main_area, text="Activity Log", font=("Inter", 10, "bold"), bg="#F1F5F9", fg="#475569").pack(anchor="w", pady=(20, 5))
        self.log_area = scrolledtext.ScrolledText(self.main_area, height=8, bg="#FFFFFF", borderwidth=0, font=("Menlo", 9), highlightthickness=1, highlightbackground="#E2E8F0")
        self.log_area.pack(fill=tk.BOTH, expand=True)

    def render_history_tab(self):
        tk.Label(self.main_area, text="Audit History", font=("Inter", 18, "bold"), bg="#F1F5F9", fg="#0F172A").pack(anchor="w", pady=(0, 20))
        
        container = tk.Frame(self.main_area, bg="#FFFFFF", padx=20, pady=20, highlightthickness=1, highlightbackground="#E2E8F0")
        container.pack(fill=tk.BOTH, expand=True)
        
        cols = ("Timestamp", "Excel Filename", "Reports", "Audit")
        self.tree = ttk.Treeview(container, columns=cols, show="headings", height=15)
        for c in cols: self.tree.heading(c, text=c)
        self.tree.column("Timestamp", width=150)
        self.tree.column("Excel Filename", width=350)
        self.tree.column("Reports", width=100, anchor="center")
        self.tree.column("Audit", width=100, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        btn_bar = tk.Frame(container, bg="#FFFFFF", pady=15)
        btn_bar.pack(fill=tk.X)
        tk.Button(btn_bar, text="Open Result Folder", font=("Inter", 10, "bold"), bg="#F1F5F9", relief="flat", padx=20, pady=10, command=self.open_selected).pack(side=tk.LEFT)
        tk.Label(btn_bar, text="Double-click row to open folder", font=("Inter", 8), bg="#FFFFFF", fg="#94A3B8").pack(side=tk.LEFT, padx=20)
        
        # Load Data
        for h in get_recent_history():
            self.tree.insert("", tk.END, values=(h[0], h[1], h[2], "POA"), tags=(h[3],))
        self.tree.bind("<Double-1>", lambda e: self.open_selected())

    def render_about_tab(self):
        tk.Label(self.main_area, text="System Information", font=("Inter", 18, "bold"), bg="#F1F5F9", fg="#0F172A").pack(anchor="w", pady=(0, 30))
        card = tk.Frame(self.main_area, bg="#FFFFFF", padx=40, pady=40, highlightthickness=1, highlightbackground="#E2E8F0")
        card.pack(fill=tk.X)
        
        info = [
            ("Application", "IDFC First Bank Audit Engine"),
            ("Version", "2.0.0 (Enterprise)"),
            ("Database", f"SQLite 3 ({DB_PATH})"),
            ("PDF Engine", "ReportLab 3.6+"),
            ("Data Engine", "Pandas & OpenPyXL"),
            ("Status", "Operational")
        ]
        for k, v in info:
            row = tk.Frame(card, bg="#FFFFFF", pady=5)
            row.pack(fill=tk.X)
            tk.Label(row, text=f"{k}:", font=("Inter", 10, "bold"), bg="#FFFFFF", width=15, anchor="w").pack(side=tk.LEFT)
            tk.Label(row, text=v, font=("Inter", 10), bg="#FFFFFF", fg="#475569").pack(side=tk.LEFT)

    def create_stat_card(self, parent, title, val, color, col):
        card = tk.Frame(parent, bg="#FFFFFF", padx=20, pady=20, highlightthickness=1, highlightbackground="#E2E8F0")
        card.grid(row=0, column=col, sticky="nsew", padx=8)
        parent.grid_columnconfigure(col, weight=1)
        tk.Label(card, text=title.upper(), font=("Inter", 7, "bold"), bg="#FFFFFF", fg="#64748B").pack(anchor="w")
        lbl = tk.Label(card, text=val, font=("Inter", 15, "bold"), bg="#FFFFFF", fg=color)
        lbl.pack(anchor="w", pady=(5, 0))
        return lbl

    def create_input_field(self, parent, label, var_name, cmd, btn_txt):
        tk.Label(parent, text=label, font=("Inter", 9, "bold"), bg="#FFFFFF", fg="#1E293B").pack(anchor="w")
        row = tk.Frame(parent, bg="#FFFFFF")
        row.pack(fill=tk.X, pady=(5, 2))
        var = tk.StringVar()
        setattr(self, var_name, var)
        tk.Entry(row, textvariable=var, bg="#F8FAFC", font=("Inter", 10), relief="flat", highlightthickness=1, highlightbackground="#CBD5E1").pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0, 10))
        tk.Button(row, text=btn_txt, font=("Inter", 8, "bold"), bg="#E2E8F0", relief="flat", padx=15, pady=8, cursor="hand2", command=cmd).pack(side=tk.LEFT)

    def log(self, msg): self.log_queue.put(msg)
    def check_log_queue(self):
        while not self.log_queue.empty():
            self.log_area.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {self.log_queue.get()}\n")
            self.log_area.see(tk.END)
        self.root.after(100, self.check_log_queue)

    def browse_in(self):
        f = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx *.xls")])
        if f: 
            self.file_var.set(f)
            self.lbl_file_info.config(text=f"Loaded: {os.path.basename(f)}", fg="#059669")
    def browse_out(self):
        f = filedialog.askdirectory()
        if f: self.folder_var.set(f)

    def update_stats_labels(self):
        if self.active_tab == "PROCESS":
            e, p = get_stats()
            self.card_excels.config(text=str(e))
            self.card_pdfs.config(text=str(p))

    def open_selected(self):
        sel = self.tree.selection()
        if sel:
            path = self.tree.item(sel[0], "tags")[0]
            if os.path.exists(path):
                if sys.platform == "win32": os.startfile(path)
                else: os.system(f'open "{path}"')
            else: messagebox.showerror("Error", "Path not found.")

    def start_process(self):
        inp, out, typ = self.file_var.get().strip(), self.folder_var.get().strip(), self.typ_var.get().strip()
        if not inp or not os.path.exists(inp): return messagebox.showerror("Error", "Invalid file source.")
        self.btn_run.config(state=tk.DISABLED, text="ENGINE RUNNING...", bg="#94A3B8")
        self.card_status.config(text="ACTIVE", fg="#1E40AF")
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
            log_generation(excel_name, count, out, typ)
            self.log(f"COMPLETED: {count} reports generated.")
            self.root.after(0, self.update_stats_labels)
            self.root.after(0, lambda: messagebox.showinfo("Engine Report", f"Batch completed successfully.\nGenerated: {count} PDFs\nSaved to: {out}"))
        except Exception as e:
            self.log(f"ENGINE FAILURE: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Engine Failure", str(e)))
        finally:
            self.root.after(0, lambda: (self.btn_run.config(state=tk.NORMAL, text="START ENGINE", bg="#1E40AF"), self.card_status.config(text="STANDBY", fg="#64748B")))

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()