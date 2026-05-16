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

def get_recent_history(limit=10):
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
# APP - ULTIMATE TRACKING DASHBOARD
# =========================================================
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("IDFC PDF Audit Professional")
        self.root.geometry("900x900")
        self.root.configure(bg="#F0F2F5")
        
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.setup_ui()
        self.update_dashboard()
        
        self.log_queue = queue.Queue()
        self.root.after(100, self.check_log_queue)

    def setup_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#101820", height=70)
        header.pack(fill=tk.X)
        tk.Label(header, text="IDFC FIRST BANK AUDIT ENGINE", font=("Helvetica", 14, "bold"), bg="#101820", fg="#FFFFFF").pack(side=tk.LEFT, padx=30, pady=20)
        
        # Dashboard Wrapper
        main_scroll = tk.Frame(self.root, bg="#F0F2F5")
        main_scroll.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Stats Cards
        stats_frame = tk.Frame(main_scroll, bg="#F0F2F5")
        stats_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.lbl_stat_excels = self.create_card(stats_frame, "Excels Processed", "0", "#004B87", 0)
        self.lbl_stat_pdfs = self.create_card(stats_frame, "PDFs Generated", "0", "#D21034", 1)
        self.lbl_stat_status = self.create_card(stats_frame, "System Status", "READY", "#2E7D32", 2)

        # Content Area (Two Columns)
        content = tk.Frame(main_scroll, bg="#F0F2F5")
        content.pack(fill=tk.BOTH, expand=True)
        
        # Left Panel (Actions)
        left = tk.Frame(content, bg="#FFFFFF", padx=20, pady=20, highlightthickness=1, highlightbackground="#DCDFE3")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        tk.Label(left, text="GENERATION WORKFLOW", font=("Helvetica", 10, "bold"), bg="#FFFFFF", fg="#101820").pack(anchor="w", pady=(0, 15))
        
        self.create_input(left, "Source Excel File", "file_var", self.browse_in, "Browse")
        self.lbl_file_hint = tk.Label(left, text="No file selected", font=("Helvetica", 8), bg="#FFFFFF", fg="#606770")
        self.lbl_file_hint.pack(anchor="w", pady=(0, 15))

        self.create_input(left, "Output Directory", "folder_var", self.browse_out, "Set Path")
        self.folder_var.set(os.path.join(os.path.expanduser("~"), "Desktop"))
        
        tk.Label(left, text="Audit Type", font=("Helvetica", 9, "bold"), bg="#FFFFFF", fg="#101820").pack(anchor="w", pady=(10, 5))
        self.typ_var = tk.StringVar(value="POA")
        tf = tk.Frame(left, bg="#FFFFFF")
        tf.pack(anchor="w", pady=(0, 15))
        for t in ["POA", "TAF"]:
            tk.Radiobutton(tf, text=t, variable=self.typ_var, value=t, bg="#FFFFFF", font=("Helvetica", 10)).pack(side=tk.LEFT, padx=(0, 20))

        self.btn_run = tk.Button(left, text="EXECUTE BATCH GENERATION", bg="#D21034", fg="#FFFFFF", font=("Helvetica", 11, "bold"), relief="flat", padx=20, pady=12, cursor="hand2", command=self.start_process)
        self.btn_run.pack(fill=tk.X, pady=10)

        # Right Panel (Recent History)
        right = tk.Frame(content, bg="#FFFFFF", padx=20, pady=20, highlightthickness=1, highlightbackground="#DCDFE3")
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        tk.Label(right, text="RECENT ACTIVITY HISTORY", font=("Helvetica", 10, "bold"), bg="#FFFFFF", fg="#101820").pack(anchor="w", pady=(0, 10))
        
        self.history_tree = ttk.Treeview(right, columns=("Time", "File", "Count"), show="headings", height=10)
        self.history_tree.heading("Time", text="Time")
        self.history_tree.heading("File", text="Excel Filename")
        self.history_tree.heading("Count", text="PDFs")
        self.history_tree.column("Time", width=120)
        self.history_tree.column("File", width=150)
        self.history_tree.column("Count", width=50)
        self.history_tree.pack(fill=tk.BOTH, expand=True)
        
        tk.Button(right, text="Open Selected Folder", command=self.open_selected_folder, bg="#F0F2F5", font=("Helvetica", 9)).pack(fill=tk.X, pady=5)

        # Log Area
        tk.Label(self.root, text="DETAILED PROCESS LOG", font=("Helvetica", 9, "bold"), bg="#F0F2F5", fg="#606770").pack(anchor="w", padx=20, pady=(15, 5))
        self.log_area = scrolledtext.ScrolledText(self.root, height=10, bg="#FFFFFF", fg="#1C1E21", font=("Consolas", 9), borderwidth=0)
        self.log_area.pack(fill=tk.X, padx=20, pady=(0, 20))

    def create_card(self, parent, title, val, color, col):
        card = tk.Frame(parent, bg="#FFFFFF", padx=15, pady=15, highlightthickness=1, highlightbackground="#DCDFE3")
        card.grid(row=0, column=col, sticky="nsew", padx=5)
        parent.grid_columnconfigure(col, weight=1)
        tk.Label(card, text=title, font=("Helvetica", 8, "bold"), bg="#FFFFFF", fg="#606770").pack(anchor="w")
        lbl = tk.Label(card, text=val, font=("Helvetica", 16, "bold"), bg="#FFFFFF", fg=color)
        lbl.pack(anchor="w", pady=(5, 0))
        return lbl

    def create_input(self, parent, label, var_name, cmd, btn_txt):
        tk.Label(parent, text=label, font=("Helvetica", 9, "bold"), bg="#FFFFFF", fg="#101820").pack(anchor="w")
        row = tk.Frame(parent, bg="#FFFFFF")
        row.pack(fill=tk.X, pady=(5, 0))
        var = tk.StringVar()
        setattr(self, var_name, var)
        tk.Entry(row, textvariable=var, bg="#F0F2F5", relief="flat", highlightthickness=1, highlightbackground="#DCDFE3").pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=(0, 10))
        tk.Button(row, text=btn_txt, command=cmd, bg="#F0F2F5", font=("Helvetica", 9)).pack(side=tk.LEFT)

    def log(self, msg): self.log_queue.put(msg)
    def check_log_queue(self):
        while not self.log_queue.empty():
            self.log_area.insert(tk.END, f"> {self.log_queue.get()}\n")
            self.log_area.see(tk.END)
        self.root.after(100, self.check_log_queue)

    def browse_in(self):
        f = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx *.xls")])
        if f: 
            self.file_var.set(f)
            self.lbl_file_hint.config(text=f"Ready: {os.path.basename(f)}", fg="#2E7D32")
    def browse_out(self):
        f = filedialog.askdirectory()
        if f: self.folder_var.set(f)

    def update_dashboard(self):
        e, p = get_stats()
        self.lbl_stat_excels.config(text=str(e))
        self.lbl_stat_pdfs.config(text=str(p))
        
        # Update Treeview
        for item in self.history_tree.get_children(): self.history_tree.delete(item)
        for h in get_recent_history():
            self.history_tree.insert("", tk.END, values=(h[0], h[1], h[2]), tags=(h[3],))

    def open_selected_folder(self):
        sel = self.history_tree.selection()
        if sel:
            path = self.history_tree.item(sel[0], "tags")[0]
            if os.path.exists(path):
                if sys.platform == "win32": os.startfile(path)
                else: os.system(f'open "{path}"')
            else: messagebox.showerror("Error", "Folder no longer exists.")

    def start_process(self):
        inp, out, typ = self.file_var.get().strip(), self.folder_var.get().strip(), self.typ_var.get().strip()
        if not inp or not os.path.exists(inp): return messagebox.showerror("Error", "Please select an Excel file.")
        self.btn_run.config(state=tk.DISABLED, text="GENERATING...")
        self.lbl_stat_status.config(text="BUSY", fg="#D21034")
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
                name = str(br[0].get("CurrentBranchName", ""))
                st = str(br[0].get("State", ""))
                safe = name.replace("/", "_").replace("\\", "_") if name else str(c)
                path = os.path.join(out, f"{safe}_{typ}.pdf")
                self.log(f"Saving: {os.path.basename(path)}")
                generate_pdf_original(typ, c, name, st, br, path)
                count += 1
            
            log_generation(excel_name, count, out, typ)
            self.root.after(0, self.update_dashboard)
            self.log(f"SUCCESS: Generated {count} reports.")
            self.root.after(0, lambda: messagebox.showinfo("Done", f"Generated {count} PDFs in:\n{out}"))
        except Exception as e:
            self.log(f"ERROR: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.root.after(0, lambda: self.btn_run.config(state=tk.NORMAL, text="EXECUTE BATCH GENERATION"))
            self.root.after(0, lambda: self.lbl_stat_status.config(text="READY", fg="#2E7D32"))

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()