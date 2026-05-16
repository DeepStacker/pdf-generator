#!/usr/bin/env python3
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import threading
import os
import sys
import queue
import time
import json
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
# ASSET & STATS HANDLING
# =========================================================
def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

FONT_DIR = get_resource_path("fonts")
os.makedirs(FONT_DIR, exist_ok=True)

# Stats file path
STATS_FILE = os.path.join(os.path.expanduser("~"), ".idfc_pdf_stats.json")

def load_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"total_excels": 0, "total_pdfs": 0, "last_run": "Never"}

def save_stats(stats):
    try:
        with open(STATS_FILE, 'w') as f: json.dump(stats, f)
    except: pass

# Font Download Logic (Original Logic Restored)
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
# CORE LOGIC
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
# APP - PREMIUM DASHBOARD UI
# =========================================================
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("IDFC PDF Report Dashboard")
        self.root.geometry("800x850")
        self.root.configure(bg="#F8F9FA")
        
        self.stats = load_stats()
        
        # UI Styling
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TFrame", background="#F8F9FA")
        self.style.configure("Card.TFrame", background="#FFFFFF", relief="flat", borderwidth=1)
        
        self.setup_ui()
        
        self.log_queue = queue.Queue()
        self.root.after(100, self.check_log_queue)

    def setup_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#1A237E", height=80)
        header.pack(fill=tk.X)
        tk.Label(header, text="IDFC FIRST BANK", font=("Helvetica", 18, "bold"), bg="#1A237E", fg="#FFFFFF").pack(side=tk.LEFT, padx=30, pady=20)
        tk.Label(header, text="PDF GENERATOR DASHBOARD", font=("Helvetica", 10), bg="#1A237E", fg="#C5CAE9").pack(side=tk.RIGHT, padx=30, pady=25)

        # Main Content
        self.container = tk.Frame(self.root, bg="#F8F9FA", padx=30, pady=20)
        self.container.pack(fill=tk.BOTH, expand=True)

        # Stats Row
        stats_frame = tk.Frame(self.container, bg="#F8F9FA")
        stats_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.create_stat_card(stats_frame, "Total Excels", str(self.stats["total_excels"]), "#3F51B5", 0)
        self.create_stat_card(stats_frame, "Total PDFs", str(self.stats["total_pdfs"]), "#43A047", 1)
        self.create_stat_card(stats_frame, "Last Generation", self.stats["last_run"], "#F4511E", 2)

        # Action Area
        action_card = tk.Frame(self.container, bg="#FFFFFF", padx=25, pady=25, highlightbackground="#E0E0E0", highlightthickness=1)
        action_card.pack(fill=tk.X, pady=10)

        # File Selection
        self.create_action_row(action_card, "Step 1: Source Excel File", "Browse File", self.browse_in, "file_var")
        self.lbl_file_info = tk.Label(action_card, text="Select an Excel file to begin...", font=("Helvetica", 9), bg="#FFFFFF", fg="#757575")
        self.lbl_file_info.pack(anchor="w", padx=5, pady=(0, 15))

        # Folder Selection
        self.create_action_row(action_card, "Step 2: Output Destination", "Select Folder", self.browse_out, "folder_var")
        default_folder = os.path.join(os.path.expanduser("~"), "Desktop")
        self.folder_var.set(default_folder)
        self.lbl_folder_info = tk.Label(action_card, text=f"Target: {default_folder}", font=("Helvetica", 9), bg="#FFFFFF", fg="#757575")
        self.lbl_folder_info.pack(anchor="w", padx=5, pady=(0, 15))

        # Audit Type
        type_frame = tk.Frame(action_card, bg="#FFFFFF")
        type_frame.pack(fill=tk.X, pady=10)
        tk.Label(type_frame, text="Step 3: Select Audit Type", font=("Helvetica", 11, "bold"), bg="#FFFFFF", fg="#212121").pack(side=tk.LEFT)
        self.typ_var = tk.StringVar(value="POA")
        for t in ["POA", "TAF"]:
            tk.Radiobutton(type_frame, text=t, variable=self.typ_var, value=t, bg="#FFFFFF", font=("Helvetica", 10)).pack(side=tk.LEFT, padx=15)

        # Run Button
        self.btn_run = tk.Button(action_card, text="START GENERATION PROCESS", font=("Helvetica", 12, "bold"), bg="#1A237E", fg="#FFFFFF", activebackground="#303F9F", activeforeground="#FFFFFF", cursor="hand2", relief="flat", padx=30, pady=12, command=self.start_process)
        self.btn_run.pack(fill=tk.X, pady=(20, 0))

        # Log Area
        tk.Label(self.container, text="SYSTEM ACTIVITY LOG", font=("Helvetica", 10, "bold"), bg="#F8F9FA", fg="#616161").pack(anchor="w", pady=(20, 5))
        self.log_area = scrolledtext.ScrolledText(self.container, height=12, bg="#FFFFFF", fg="#212121", font=("Courier New", 10), relief="flat", highlightbackground="#E0E0E0", highlightthickness=1)
        self.log_area.pack(fill=tk.BOTH, expand=True)

    def create_stat_card(self, parent, title, value, color, col):
        card = tk.Frame(parent, bg="#FFFFFF", padx=15, pady=15, highlightbackground="#E0E0E0", highlightthickness=1)
        card.grid(row=0, column=col, sticky="nsew", padx=5)
        parent.grid_columnconfigure(col, weight=1)
        
        tk.Label(card, text=title, font=("Helvetica", 9, "bold"), bg="#FFFFFF", fg="#757575").pack(anchor="w")
        lbl_val = tk.Label(card, text=value, font=("Helvetica", 14, "bold"), bg="#FFFFFF", fg=color)
        lbl_val.pack(anchor="w", pady=(5, 0))
        
        # Store label ref to update later
        if title == "Total Excels": self.lbl_stat_excels = lbl_val
        elif title == "Total PDFs": self.lbl_stat_pdfs = lbl_val
        elif title == "Last Generation": self.lbl_stat_last = lbl_val

    def create_action_row(self, parent, label_text, btn_text, cmd, var_name):
        tk.Label(parent, text=label_text, font=("Helvetica", 11, "bold"), bg="#FFFFFF", fg="#212121").pack(anchor="w")
        row = tk.Frame(parent, bg="#FFFFFF")
        row.pack(fill=tk.X, pady=(5, 2))
        var = tk.StringVar()
        setattr(self, var_name, var)
        entry = tk.Entry(row, textvariable=var, font=("Helvetica", 10), bg="#F5F5F5", relief="flat", highlightbackground="#E0E0E0", highlightthickness=1)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0, 10))
        btn = tk.Button(row, text=btn_text, font=("Helvetica", 9, "bold"), bg="#EEEEEE", relief="flat", padx=15, pady=8, cursor="hand2", command=cmd)
        btn.pack(side=tk.LEFT)

    def log(self, msg): self.log_queue.put(msg)
    def check_log_queue(self):
        while not self.log_queue.empty():
            self.log_area.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {self.log_queue.get()}\n")
            self.log_area.see(tk.END)
        self.root.after(100, self.check_log_queue)

    def browse_in(self):
        f = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if f:
            self.file_var.set(f)
            self.lbl_file_info.config(text=f"Selected: {os.path.basename(f)}", fg="#43A047")
    def browse_out(self):
        f = filedialog.askdirectory()
        if f:
            self.folder_var.set(f)
            self.lbl_folder_info.config(text=f"Target: {f}", fg="#1A237E")

    def start_process(self):
        inp, out, typ = self.file_var.get().strip(), self.folder_var.get().strip(), self.typ_var.get().strip()
        if not inp or not os.path.exists(inp): return messagebox.showerror("Error", "Please select a valid source Excel file.")
        excel_name = os.path.splitext(os.path.basename(inp))[0]
        specific_out = os.path.join(out, f"{excel_name}_{int(time.time())}")
        self.btn_run.config(state=tk.DISABLED, text="PROCESSING...", bg="#BDBDBD")
        self.log_area.delete(1.0, tk.END)
        threading.Thread(target=self.worker, args=(inp, specific_out, typ), daemon=True).start()

    def worker(self, inp, out, typ):
        try:
            os.makedirs(out, exist_ok=True)
            s, h, rows = read_excel_original(inp, self.log)
            groups = {}
            for r in rows:
                b = str(r.get("CurrentBranch", "UNKNOWN")).strip()
                groups.setdefault(b, []).append(r)
            
            pdf_count = 0
            for c, br in sorted(groups.items()):
                name = str(br[0].get("CurrentBranchName", ""))
                st = str(br[0].get("State", ""))
                safe = name.replace("/", "_").replace("\\", "_") if name else str(c)
                path = os.path.join(out, f"{safe}_{typ}.pdf")
                self.log(f"Generating: {os.path.basename(path)}")
                generate_pdf_original(typ, c, name, st, br, path)
                pdf_count += 1
            
            # Update Stats
            self.stats["total_excels"] += 1
            self.stats["total_pdfs"] += pdf_count
            self.stats["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            save_stats(self.stats)
            self.update_dashboard()
            
            self.log(f"\nSUCCESS! Processed 1 Excel and generated {pdf_count} PDFs.")
            self.root.after(0, lambda: messagebox.showinfo("Process Complete", f"Successfully generated {pdf_count} reports in:\n{out}"))
        except Exception as e:
            self.log(f"CRITICAL ERROR: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("System Error", str(e)))
        finally:
            self.root.after(0, lambda: self.btn_run.config(state=tk.NORMAL, text="START GENERATION PROCESS", bg="#1A237E"))

    def update_dashboard(self):
        self.root.after(0, lambda: self.lbl_stat_excels.config(text=str(self.stats["total_excels"])))
        self.root.after(0, lambda: self.lbl_stat_pdfs.config(text=str(self.stats["total_pdfs"])))
        self.root.after(0, lambda: self.lbl_stat_last.config(text=self.stats["last_run"]))

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()