#!/usr/bin/env python3
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import threading
import os
import sys
import queue
import time
import urllib.request
import openpyxl
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# =========================================================
# ASSET HANDLING
# =========================================================
def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

FONT_DIR = get_resource_path("fonts")
os.makedirs(FONT_DIR, exist_ok=True)

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
        except Exception: pass

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
# LOGIC
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
# APP - HIGHEST VISIBILITY FIX
# =========================================================
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("IDFC PDF Generator")
        self.root.geometry("600x750")
        
        # Explicitly set background of root to white
        self.root.configure(bg="#FFFFFF")
        
        # Container frame
        self.main = tk.Frame(self.root, bg="#FFFFFF", padx=20, pady=20)
        self.main.pack(fill=tk.BOTH, expand=True)

        # Title
        tk.Label(self.main, text="PDF Generator", font=("Helvetica", 20, "bold"), bg="#FFFFFF", fg="#000000").pack(pady=10)

        # File Selection
        self.add_section("1. Select Source Excel File:", "Browse", self.browse_in, "file")
        self.lbl_file_status = tk.Label(self.main, text="No file selected", font=("Helvetica", 9, "italic"), bg="#FFFFFF", fg="#FF0000")
        self.lbl_file_status.pack(anchor="w", padx=5, pady=(0, 10))

        # Folder Selection
        self.add_section("2. Select Destination Folder:", "Set Folder", self.browse_out, "folder")
        self.lbl_folder_status = tk.Label(self.main, text="Desktop", font=("Helvetica", 9, "italic"), bg="#FFFFFF", fg="#0000FF")
        self.lbl_folder_status.pack(anchor="w", padx=5, pady=(0, 10))

        # Audit Type Selection
        tk.Label(self.main, text="3. Audit Type:", font=("Helvetica", 11, "bold"), bg="#FFFFFF", fg="#000000").pack(anchor="w", pady=(10, 5))
        self.typ_var = tk.StringVar(value="POA")
        type_frame = tk.Frame(self.main, bg="#FFFFFF")
        type_frame.pack(anchor="w")
        for t in ["POA", "TAF"]:
            rb = tk.Radiobutton(type_frame, text=t, variable=self.typ_var, value=t, bg="#FFFFFF", fg="#000000", selectcolor="#EEEEEE", activebackground="#FFFFFF")
            rb.pack(side=tk.LEFT, padx=5)

        # Generate Button
        self.btn_run = tk.Button(self.main, text="GENERATE PDFs", font=("Helvetica", 14, "bold"), bg="#4CAF50", fg="#FFFFFF", highlightbackground="#FFFFFF", width=25, height=2, command=self.start_process)
        self.btn_run.pack(pady=20)

        # Progress / Logs
        tk.Label(self.main, text="Processing Logs:", font=("Helvetica", 10, "bold"), bg="#FFFFFF", fg="#000000").pack(anchor="w")
        self.log_area = scrolledtext.ScrolledText(self.main, height=15, bg="#F0F0F0", fg="#000000", font=("Courier", 10))
        self.log_area.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_queue = queue.Queue()
        self.root.after(100, self.check_log_queue)

    def add_section(self, label_text, btn_text, cmd, mode):
        tk.Label(self.main, text=label_text, font=("Helvetica", 11, "bold"), bg="#FFFFFF", fg="#000000").pack(anchor="w", pady=(10, 2))
        f = tk.Frame(self.main, bg="#FFFFFF")
        f.pack(fill=tk.X)
        var = tk.StringVar()
        if mode == "folder": var.set(os.path.join(os.path.expanduser("~"), "Desktop"))
        setattr(self, f"{mode}_var", var)
        entry = tk.Entry(f, textvariable=var, bg="#EEEEEE", fg="#000000", insertbackground="#000000", bd=1)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)
        btn = tk.Button(f, text=btn_text, command=cmd, bg="#E1E1E1", fg="#000000", highlightbackground="#FFFFFF")
        btn.pack(side=tk.LEFT, padx=5)

    def log(self, msg): self.log_queue.put(msg)
    def check_log_queue(self):
        while not self.log_queue.empty():
            self.log_area.insert(tk.END, f"{self.log_queue.get()}\n")
            self.log_area.see(tk.END)
        self.root.after(100, self.check_log_queue)

    def browse_in(self):
        f = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if f:
            self.file_var.set(f)
            self.lbl_file_status.config(text=f"SELECTED: {os.path.basename(f)}", fg="#228B22")
    def browse_out(self):
        f = filedialog.askdirectory()
        if f:
            self.folder_var.set(f)
            self.lbl_folder_status.config(text=f"SAVE TO: {os.path.basename(f)}", fg="#0000FF")

    def start_process(self):
        inp, out, typ = self.file_var.get().strip(), self.folder_var.get().strip(), self.typ_var.get().strip()
        if not inp or not os.path.exists(inp): return messagebox.showerror("Error", "Please select a valid Excel file first.")
        excel_name = os.path.splitext(os.path.basename(inp))[0]
        specific_out = os.path.join(out, f"{excel_name}_{int(time.time())}")
        self.btn_run.config(state=tk.DISABLED, text="GENERATING...")
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
            for c, br in sorted(groups.items()):
                name = str(br[0].get("CurrentBranchName", ""))
                st = str(br[0].get("State", ""))
                safe = name.replace("/", "_").replace("\\", "_") if name else str(c)
                path = os.path.join(out, f"{safe}_{typ}.pdf")
                self.log(f"GEN: {os.path.basename(path)}")
                generate_pdf_original(typ, c, name, st, br, path)
            self.log("\n--- COMPLETED SUCCESSFULLY! ---")
            self.log(f"All files saved in folder:\n{out}")
            self.root.after(0, lambda: messagebox.showinfo("Success", f"PDFs generated successfully in:\n{out}"))
        except Exception as e:
            self.log(f"ERROR: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.root.after(0, lambda: self.btn_run.config(state=tk.NORMAL, text="GENERATE PDFs"))

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()