import os
import sys
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
# UTILITIES
# =========================================================
def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# =========================================================
# CONSTANTS & ASSETS
# =========================================================
FONT_DIR = get_resource_path("fonts")
REG_PATH = os.path.join(FONT_DIR, "Carlito-Regular.ttf")
BOLD_PATH = os.path.join(FONT_DIR, "Arimo-Bold.ttf")

# Pre-load fonts if available
try:
    pdfmetrics.registerFont(TTFont('Carlito', REG_PATH))
    pdfmetrics.registerFont(TTFont('ArimoBold', BOLD_PATH))
    FONT_REG = 'Carlito'
    FONT_BLD = 'ArimoBold'
except:
    FONT_REG = 'Helvetica'
    FONT_BLD = 'Helvetica-Bold'

REQUIRED_COLUMNS = ["Prospectno", "CUID", "Tare Weight", "State", "CurrentBranch", "CurrentBranchName"]

# =========================================================
# CORE LOGIC
# =========================================================
def format_tare_weight(val):
    if pd.isna(val) or val == "" or val is None:
        return ""
    try:
        fval = float(val)
        return str(int(fval)) if fval == int(fval) else str(fval)
    except:
        return str(val)

def read_excel(excel_path, log_callback=print):
    log_callback(f"Reading Excel: {os.path.basename(excel_path)}")
    wb = openpyxl.load_workbook(excel_path, data_only=True, read_only=True)
    required_lower = [c.lower() for c in REQUIRED_COLUMNS]
    target_sheet = None
    
    for sname in wb.sheetnames:
        ws = wb[sname]
        try:
            header_row = [str(cell.value).strip().replace("\n", "") if cell.value else "" for cell in next(ws.iter_rows(min_row=1, max_row=1))]
            if all(r in [h.lower() for h in header_row] for r in required_lower):
                target_sheet = sname
                break
        except StopIteration:
            continue
    
    if not target_sheet:
        raise Exception("No valid sheet found with required columns.")
    
    log_callback(f"Found valid sheet: {target_sheet}")
    ws = wb[target_sheet]
    headers = [str(cell.value).strip().replace("\n", "") if cell.value else "" for cell in next(ws.iter_rows(min_row=1, max_row=1))]
    
    rows = []
    for row in ws.iter_rows(min_row=2, values_only=False):
        row_data, all_none = {}, True
        for i, cell in enumerate(row):
            if i < len(headers) and headers[i]:
                val = cell.value
                if val is not None:
                    all_none = False
                if headers[i] in ("Prospectno", "CUID"):
                    row_data[headers[i]] = str(val).strip() if val is not None else ""
                else:
                    row_data[headers[i]] = val
        if not all_none:
            rows.append(row_data)
            
    return target_sheet, headers, rows

def generate_pdf(audit_type, branch_code, branch_name, state, rows, output_path):
    PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)
    doc = SimpleDocTemplate(
        output_path, 
        pagesize=(PAGE_WIDTH, PAGE_HEIGHT), 
        leftMargin=50.2, 
        rightMargin=50.2, 
        topMargin=48, 
        bottomMargin=15, 
        title=os.path.basename(output_path)
    )
    
    cw = [22.2, 101.1, 118.5, 60.3, 67.2, 125.0, 247.3]
    style_hdr = ParagraphStyle("ColHdr", fontName=FONT_BLD, fontSize=9, alignment=TA_CENTER, leading=10, spaceBefore=0, spaceAfter=0)
    
    table_data = [
        ["Audit Type :", "", str(audit_type), "", "Branch Name :", "", str(branch_name)],
        ["Branch Code :", "", str(branch_code), "", "State :", "", str(state)],
        [
            Paragraph("Sr<br/>No", style_hdr), 
            Paragraph("Prospectno", style_hdr), 
            Paragraph("CUID", style_hdr), 
            Paragraph("Tare Weight<br/>as per Bank", style_hdr), 
            Paragraph("<nobr>Tare Weight as</nobr><br/>per Audit", style_hdr), 
            Paragraph("<nobr>Purity Check - 18K and</nobr><br/><nobr>above 18K or Below 18K</nobr>", style_hdr), 
            Paragraph("Remarks", style_hdr)
        ]
    ]
    
    for idx, row in enumerate(rows, 1):
        table_data.append([
            str(idx), 
            str(row.get("Prospectno", "")), 
            str(row.get("CUID", "")), 
            format_tare_weight(row.get("Tare Weight", "")), 
            "", "", ""
        ])
    
    row_heights = [12.2, 14.2, 22.5] + [30.5] * (len(table_data) - 3)
    table = Table(table_data, colWidths=cw, rowHeights=row_heights, repeatRows=3)
    
    style_cmds = [
        ("SPAN", (0, 0), (1, 0)), ("SPAN", (4, 0), (5, 0)), ("SPAN", (0, 1), (1, 1)), ("SPAN", (4, 1), (5, 1)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 1), FONT_BLD), ("FONTSIZE", (0, 0), (-1, 1), 9),
        ("FONTNAME", (0, 3), (-1, -1), FONT_REG), ("FONTSIZE", (0, 3), (-1, -1), 9),
        ("FONTNAME", (0, 3), (0, -1), FONT_BLD),
        ("BACKGROUND", (0, 2), (3, 2), colors.HexColor("#FFFF00")),
        ("BACKGROUND", (4, 2), (6, 2), colors.HexColor("#4985E8")),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 1), ("RIGHTPADDING", (0, 0), (-1, -1), 1),
        ("LINEBEFORE", (0, 0), (0, -1), 0.5, colors.black), ("LINEAFTER", (6, 0), (6, -1), 0.5, colors.black),
        ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.black), ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.black),
        ("GRID", (0, 0), (2, 1), 0.5, colors.black), ("GRID", (4, 0), (6, 1), 0.5, colors.black),
        ("GRID", (0, 2), (-1, -1), 0.5, colors.black),
    ]
    table.setStyle(TableStyle(style_cmds))
    doc.build([table])
