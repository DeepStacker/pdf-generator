"""Report Validator & Branch Tracking API routes (ported from report_automation).

Registers bottle routes on the default app for:
  POST /api/report/upload                 - validate an xlsx (optionally reorder by PDF)
  POST /api/report/download               - download the validated/edited workbook
  GET  /api/report/tracking               - list tracking records
  POST /api/report/tracking               - create tracking record
  PUT  /api/report/tracking/<id>          - update tracking record
  DELETE /api/report/tracking/<id>        - delete tracking record
"""

import datetime
import os
import re
import uuid
from copy import copy
from pathlib import Path
from tempfile import NamedTemporaryFile

import openpyxl
from openpyxl.styles import PatternFill, Font
from openpyxl.utils import get_column_letter

from audit_engine.lib.bottle import route, request, response, static_file, HTTPError

from audit_engine_web import report_validator as rv
from audit_engine_web import tracking

REPORT_UPLOAD_DIR = Path(__file__).resolve().parent.parent / "report_uploads"
REPORT_UPLOAD_DIR.mkdir(exist_ok=True)

SESSION_DATA = {}

FILL_HEX = {
    "DARK_RED": "8B0000",
    "LIGHT_RED": "FFC7CE",
    "ORANGE": "FF8C00",
    "YELLOW": "FFFF00",
    "GREEN": "C6EFCE",
    "LIGHT_BLUE": "BDD7EE",
}

FILL_MAP = {
    "8B0000": "#8B0000",
    "FFC7CE": "#FFC7CE",
    "FF8C00": "#FF8C00",
    "FFFF00": "#FFFF00",
    "C6EFCE": "#C6EFCE",
    "BDD7EE": "#BDD7EE",
}


def secure_delete(path):
    """Overwrite file with random data before deleting (unrecoverable)."""
    if not path or not os.path.exists(path):
        return
    try:
        size = os.path.getsize(path)
        with open(path, "wb") as f:
            chunk_size = min(size, 65536)
            for _ in range(3):
                f.seek(0)
                remaining = size
                while remaining > 0:
                    chunk = os.urandom(min(chunk_size, remaining))
                    f.write(chunk)
                    remaining -= len(chunk)
                f.flush()
                os.fsync(f.fileno())
        os.unlink(path)
    except OSError:
        pass


def cell_ref(row, col_idx):
    return f"{get_column_letter(col_idx)}{row}"


def json_safe(val):
    """Convert non-JSON-serializable cell values (dates) to strings."""
    if isinstance(val, (datetime.datetime, datetime.date)):
        return val.isoformat()
    if isinstance(val, (datetime.time)):
        return val.isoformat()
    return val


def run_validation_and_extract(filepath, file_id, original_name=None, pdf_path=None):
    wb = openpyxl.load_workbook(filepath, keep_vba=False, keep_links=False)
    wb_data = openpyxl.load_workbook(filepath, data_only=True, keep_vba=False, keep_links=False)
    sheet_name = "Purity Verification Format"
    if sheet_name not in wb.sheetnames:
        available = wb.sheetnames
        raise KeyError(f"Sheet '{sheet_name}' not found. Available sheets: {available}")
    ws = wb[sheet_name]
    ws_data = wb_data[sheet_name]

    col = rv.map_columns(ws)
    data_start = 5
    data_end = rv.find_data_end(ws, data_start)

    col_map = {
        "packet": rv.get_col(col, "PACKET NO."),
        "account": rv.get_col(col, "ACCOUNT NUMBER"),
        "applicant": rv.get_col(col, "APPLICANT NAME"),
        "status": rv.get_col(col, "FRESH/RENEWAL/CLOSED/ALREADY VERIFIED"),
        "taf": rv.get_col(col, "TAF/POA"),
        "remarks": rv.get_col(col, "AGENCY REMARKS"),
        "magnet": rv.get_col(col, "MAGNET TEST RESULT"),
        "tampered": rv.get_col(col, "PACKET TAMPERED YES/NO"),
        "gdr_gross": rv.get_col(col, "GROSS WEIGHT AS PER GDR/PACKET"),
        "actual_gross": rv.get_col(col, "ACTUAL GROSS WEIGHT AS PER FCU AGENCY VERIFICATION"),
        "tare": rv.get_col(col, "ACTUAL TARE WEIGHT AS PER FCU AGENCY VERIFICATION"),
        "gross_diff": rv.get_col(col, "DIFFERENCE IN GROSS WEIGHT"),
        "gdr_net": rv.get_col(col, "NET WEIGHT AS PER GDR/PACKET"),
        "actual_net": rv.get_col(col, "ACTUAL NET WEIGHT AS PER FCU AGENCY VERIFICATION"),
        "net_diff": rv.get_col(col, "DIFFERENCE IN NET WEIGHT"),
        "spur_count": rv.get_col(col, "TOTAL NO.OF SPURIOUS ORNAMENTS"),
        "spur_weight": rv.get_col(col, "SPURIOUS ORNAMENTS GROSS WEIGHT"),
        "spur_pct": rv.get_col(col, "% OF SPURIOUS ORNAMENTS GROSS WEIGHT"),
        "carat_count": rv.get_col(col, "TOTAL NO.OF ORNAMENTS WITH CARAT MISMATCH"),
        "uncommon_count": rv.get_col(col, "TOTAL NO.OF UNCOMMON ORNAMENTS"),
        "sanction_date": rv.get_col(col, "SANCTION DATE"),
        "verification_date": rv.get_col(col, "AGENCY VERIFICATION DATE"),
        "sanction_limit": rv.get_col(col, "SANCTION LIMIT"),
        "gdr_no": rv.get_col(col, "GDR NUMBER"),
        "ornaments_gdr": rv.get_col(col, "TOTAL NO.OF ORNAMENTS AS PER THE GDR/PACKET"),
        "ornaments_actual": rv.get_col(col, "ACTUAL AVAILABLE ORNAMENTS AT THE TIME OF FCU VERIFICATION"),
        "ornaments_diff": rv.get_col(col, "DIFFRENCE IN ACTUAL ORNAMENTS"),
        "renewal_date": rv.get_col(col, "RENEWAL/CLOSED DATE"),
    }

    all_rows = list(range(data_start, data_end + 1))

    if pdf_path:
        pdf_accounts = rv.extract_accounts_from_pdf(pdf_path)
        if pdf_accounts:
            rv.rearrange_rows_by_pdf(ws, col_map, all_rows, pdf_accounts)
            rv.rearrange_rows_by_pdf(ws_data, col_map, all_rows, pdf_accounts)

    _cell_cache = {}
    for (_r, _c), _cell in list(ws._cells.items()):
        _cell_cache[(_r, _c)] = _cell

    rows_data = {}
    for r in all_rows:
        rows_data[r] = {
            "packet": rv.safe_str(_cell_cache.get((r, col_map["packet"])).value if col_map["packet"] and (r, col_map["packet"]) in _cell_cache else None),
            "account": rv.safe_str(_cell_cache.get((r, col_map["account"])).value if col_map["account"] and (r, col_map["account"]) in _cell_cache else None),
            "name": rv.safe_str(_cell_cache.get((r, col_map["applicant"])).value if col_map["applicant"] and (r, col_map["applicant"]) in _cell_cache else None),
            "status": rv.safe_str(_cell_cache.get((r, col_map["status"])).value if col_map["status"] and (r, col_map["status"]) in _cell_cache else None),
            "taf": rv.safe_str(_cell_cache.get((r, col_map["taf"])).value if col_map["taf"] and (r, col_map["taf"]) in _cell_cache else None),
            "remarks": rv.safe_str(_cell_cache.get((r, col_map["remarks"])).value if col_map["remarks"] and (r, col_map["remarks"]) in _cell_cache else None),
            "magnet": rv.safe_str(_cell_cache.get((r, col_map["magnet"])).value if col_map["magnet"] and (r, col_map["magnet"]) in _cell_cache else None),
            "tampered": rv.safe_str(_cell_cache.get((r, col_map["tampered"])).value if col_map["tampered"] and (r, col_map["tampered"]) in _cell_cache else None),
        }

    _data_cache = {}
    for (_r, _c), _cell in ws_data._cells.items():
        _data_cache[(_r, _c)] = _cell

    summary = __import__("collections").defaultdict(list)
    rv.run_validation(ws, ws_data, col_map, all_rows, rows_data, summary, _cell_cache, _data_cache)

    column_indices = []
    column_letters = []
    column_headers = []
    for c in range(1, 101):
        cell = _cell_cache.get((2, c))
        header_val = cell.value if cell else None
        if header_val and str(header_val).strip():
            column_indices.append(c)
            column_letters.append(get_column_letter(c))
            column_headers.append(str(header_val).strip())

    col_letter_map = {c: get_column_letter(c) for c in column_indices}

    rows_json = []
    highlights = {}
    issues = []

    for r in all_rows:
        row_data = {"row": r, "cells": {}}
        for c in column_indices:
            col_letter = col_letter_map[c]
            cell_obj = _cell_cache.get((r, c))
            if cell_obj is None:
                continue
            raw = cell_obj.value
            if raw is None or (isinstance(raw, str) and raw.startswith("=")):
                dc = _data_cache.get((r, c))
                if dc is not None:
                    raw = dc.value
            row_data["cells"][col_letter] = json_safe(raw)
            fill = cell_obj.fill
            if fill and fill.start_color and fill.start_color.rgb:
                rgb = str(fill.start_color.rgb)
                if rgb.startswith("00"):
                    rgb = rgb[2:]
                if rgb in FILL_MAP and rgb != "00000000":
                    key = cell_ref(r, c)
                    highlights[key] = FILL_MAP[rgb]
                    issues.append({
                        "ref": key,
                        "row": r,
                        "col": col_letter,
                        "color": FILL_MAP[rgb],
                    })
        rows_json.append(row_data)

    total_issues = sum(len(v) for v in summary.values())

    custom_filename = rv.get_custom_output_filename(ws, col, col_map, all_rows, _cell_cache, original_name)

    output_path = REPORT_UPLOAD_DIR / f"{file_id}.xlsx"
    wb.save(str(output_path))

    result = {
        "file_id": file_id,
        "file_name": original_name or Path(filepath).name,
        "custom_filename": custom_filename,
        "columns": column_headers,
        "column_letters": column_letters,
        "rows": rows_json,
        "highlights": highlights,
        "issues": issues,
        "summary": {k: len(v) for k, v in sorted(summary.items())},
        "summary_details": {k: v for k, v in sorted(summary.items())},
        "total_issues": total_issues,
    }

    wb.close()
    wb_data.close()
    return result


# ── Routes ────────────────────────────────────────────────────────────

@route("/api/report/upload", method=["OPTIONS", "POST"])
def report_upload():
    if request.method == "OPTIONS":
        return {}
    upload = request.files.get("file")
    if not upload:
        response.status = 400
        return {"detail": "No file provided"}
    original_name = upload.filename or "upload.xlsx"
    ext = Path(original_name).suffix.lower()
    if ext != ".xlsx":
        response.status = 400
        return {"detail": "Only .xlsx files are supported (.xls is not supported)"}

    file_id = uuid.uuid4().hex[:12]
    content = upload.file.read()

    src = NamedTemporaryFile(delete=False, suffix=".xlsx")
    src.write(content)
    src.close()
    temp_path = src.name

    temp_pdf_path = None
    pdf_file = request.files.get("pdf_file")
    if pdf_file:
        pdf_src = NamedTemporaryFile(delete=False, suffix=".pdf")
        pdf_src.write(pdf_file.file.read())
        pdf_src.close()
        temp_pdf_path = pdf_src.name

    try:
        result = run_validation_and_extract(temp_path, file_id, original_name, pdf_path=temp_pdf_path)
    except KeyError as e:
        secure_delete(temp_path)
        if temp_pdf_path:
            secure_delete(temp_pdf_path)
        response.status = 400
        return {"detail": f"Missing expected sheet or column: {e}"}
    except Exception as e:
        secure_delete(temp_path)
        if temp_pdf_path:
            secure_delete(temp_pdf_path)
        err_msg = str(e)
        if "zipfile" in err_msg.lower() or "bad" in err_msg.lower():
            response.status = 400
            return {"detail": "Invalid file format. Please upload a valid .xlsx file."}
        response.status = 400
        return {"detail": f"Processing error: {e}"}
    finally:
        if temp_pdf_path:
            secure_delete(temp_pdf_path)

    SESSION_DATA[file_id] = {
        "source_bytes": content,
        "source_path": temp_path,
        "output": str(REPORT_UPLOAD_DIR / f"{file_id}.xlsx"),
        "original_name": original_name,
        "custom_filename": result.get("custom_filename"),
    }
    return result


@route("/api/report/download", method=["POST"])
def report_download():
    data = request.json or {}
    file_id = data.get("file_id")
    edits = data.get("edits") or []
    if file_id not in SESSION_DATA:
        response.status = 404
        return {"detail": "Session not found"}

    session = SESSION_DATA[file_id]
    output_path = session["output"]
    if not os.path.exists(output_path):
        response.status = 404
        return {"detail": "Processed file not found"}

    original_name = session.get("original_name", "validated_report.xlsx")
    custom_name = session.get("custom_filename")
    download_name = custom_name if custom_name else (Path(original_name).stem + "_VALIDATED.xlsx")

    if not edits:
        return static_file(
            os.path.basename(output_path),
            root=os.path.dirname(output_path),
            download=download_name,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    wb = openpyxl.load_workbook(output_path)
    sheet_name = "Purity Verification Format"
    if sheet_name not in wb.sheetnames:
        wb.close()
        response.status = 500
        return {"detail": "Processed file is missing expected sheet"}
    ws = wb[sheet_name]

    source_bytes = SESSION_DATA[file_id].get("source_bytes")
    wb_orig = None
    ws_orig = None
    src_temp = None
    if source_bytes:
        src_temp = NamedTemporaryFile(delete=False, suffix=".xlsx")
        src_temp.write(source_bytes)
        src_temp.close()
        wb_orig = openpyxl.load_workbook(src_temp.name)
        ws_orig = wb_orig[sheet_name] if sheet_name in wb_orig.sheetnames else None

    for edit in edits:
        ref = edit.get("ref")
        value = edit.get("value")
        if not ref:
            continue
        match = re.match(r"^([A-Z]+)(\d+)$", str(ref))
        if match:
            col_letter = match.group(1)
            row_num = int(match.group(2))
            col_idx = openpyxl.utils.column_index_from_string(col_letter)
            cell = ws.cell(row=row_num, column=col_idx)
            cell.value = value
            if ws_orig:
                orig_cell = ws_orig.cell(row=row_num, column=col_idx)
                cell.font = copy(orig_cell.font) if orig_cell.font else Font()
                if orig_cell.fill and orig_cell.fill.start_color and orig_cell.fill.start_color.rgb:
                    cell.fill = copy(orig_cell.fill)
                else:
                    cell.fill = PatternFill()
                if orig_cell.border:
                    cell.border = copy(orig_cell.border)
                if orig_cell.number_format and orig_cell.number_format != "General":
                    cell.number_format = orig_cell.number_format
                if orig_cell.alignment:
                    cell.alignment = copy(orig_cell.alignment)
            else:
                cell.fill = PatternFill()

    if wb_orig:
        wb_orig.close()
    if src_temp:
        secure_delete(src_temp.name)

    response_path = REPORT_UPLOAD_DIR / f"final_{file_id}.xlsx"
    wb.save(str(response_path))
    wb.close()

    return static_file(
        response_path.name,
        root=str(REPORT_UPLOAD_DIR),
        download=download_name,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ── Tracking CRUD ─────────────────────────────────────────────────────

@route("/api/report/tracking", method=["OPTIONS", "GET"])
def report_tracking_list():
    if request.method == "OPTIONS":
        return {}
    return tracking.list_records()


@route("/api/report/tracking", method=["POST"])
def report_tracking_create():
    data = request.json or {}
    try:
        return tracking.create_record(data)
    except Exception as e:
        response.status = 400
        return {"detail": f"Create failed: {e}"}


@route("/api/report/tracking/<record_id:int>", method=["OPTIONS", "PUT"])
def report_tracking_update(record_id):
    if request.method == "OPTIONS":
        return {}
    data = request.json or {}
    filtered = {k: v for k, v in data.items() if v is not None}
    updated = tracking.update_record(record_id, filtered)
    if updated is None:
        response.status = 404
        return {"detail": "Record not found"}
    return updated


@route("/api/report/tracking/<record_id:int>", method=["OPTIONS", "DELETE"])
def report_tracking_delete(record_id):
    if request.method == "OPTIONS":
        return {}
    deleted = tracking.delete_record(record_id)
    if not deleted:
        response.status = 404
        return {"detail": "Record not found"}
    return {"ok": True}
