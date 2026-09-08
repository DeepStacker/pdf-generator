"""Arvog Bank PDF generation service.

The ArvogService class provides a clean API. Module-level legacy functions
delegate to a default singleton so existing callers work unchanged.
"""

import argparse
import html
import logging
import os
from collections.abc import Callable

import openpyxl
import pandas as pd
from openpyxl.styles import Alignment, Border, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

from audit_engine.services.arvog_columns import (
    ColumnKind,
    display_value,
    excel_format_for,
    format_depends_on_values,
    kind_for,
    normalize_dataframe,
)
from audit_engine.services.arvog_layout import (
    DATA_ATTR_ORDER,
    HEADER_SCAN_ROWS,
    find_header_row,
    map_ornaments,
    read_header_row,
    read_rows,
)
from audit_engine.utils.config import arvog as arvog_config

_MAX_JEWELLERY_COLUMNS = 20
logger = logging.getLogger(__name__)


# =========================================================
# CONSTANTS
# =========================================================

REQUIRED_COLUMNS = [
    "SR No.",
    "Branch",
    "Customer Name",
    "Loan No.",
    "Jewellery No.",
    "Jewellery1",
    "Gross Wt.",
    "Stone Wt.",
    "Net Wt.",
    "Karat",
    "Packets Number",
]


# =========================================================
# PDF TABLE LAYOUT
# =========================================================
# The sheet is A3 landscape (1190.55 x 841.89pt) with the margins below, so
# the columns have exactly PRINTABLE_WIDTH between them.
PAGE_LEFT_MARGIN = 85.95
PAGE_RIGHT_MARGIN = 52.5
PAGE_TOP_MARGIN = 53.78
PAGE_BOTTOM_MARGIN = 100.0
PRINTABLE_WIDTH = landscape(A3)[0] - PAGE_LEFT_MARGIN - PAGE_RIGHT_MARGIN

HEADER_FONT = "Helvetica-Bold"
HEADER_FONT_SIZE = 8.78
CELL_HORIZONTAL_PADDING = 1.0

BANNER_ROW_HEIGHT = 24.75
HEADER_ROW_HEIGHT = 24.75
DATA_ROW_HEIGHT = 38.7

# The left half is filled from the workbook; the yellow right half is the
# worksheet the auditor completes by hand at the branch.
PDF_HEADERS = [
    "SR\nNo.",
    "Customer Name",
    "Loan No.",
    "PACKET\nNUMBER",
    "Ornament\nNo.",
    "Ornament\nName",
    "Gross\nWt.",
    "Stone\nWt.",
    "Karat",
    "Net Wt.",
    "Count of\nOrnament",
    "Gross Wt.",
    "Stone Wt",
    "Net Weight",
    "Karat",
    "Remarks",
]

# Source column behind each of the first ten headers, in order.
PDF_DATA_COLUMNS = [
    "SR No.",
    "Customer Name",
    "Loan No.",
    "Packets Number",
    "Jewellery No.",
    "Jewellery1",
    "Gross Wt.",
    "Stone Wt.",
    "Karat",
    "Net Wt.",
]

AUDIT_BLOCK_FIRST_COLUMN = len(PDF_DATA_COLUMNS)


# =========================================================
# EXCEL SHEET LAYOUT
# =========================================================
# The PDF centres every cell; the converted Excel is the same report in
# another form, so it is centred to match.
#
# Nothing wraps and no row is given an explicit height, so every row — banner,
# heading and data alike — comes out at the sheet's default. A wrapping
# heading would need a taller row than the data rows beneath it.
EXCEL_CELL_ALIGNMENT = Alignment(horizontal="center", vertical="center")

# Every cell is boxed, the same as the PDF's grid.
_EXCEL_BORDER_SIDE = Side(style="thin", color="FF000000")
EXCEL_CELL_BORDER = Border(
    left=_EXCEL_BORDER_SIDE,
    right=_EXCEL_BORDER_SIDE,
    top=_EXCEL_BORDER_SIDE,
    bottom=_EXCEL_BORDER_SIDE,
)

# Column widths, in Excel character units, sized from the widest thing in the
# column — including the whole heading, which has one line to fit on. Left at
# the 8.43 default, headings like "After audit packet number" were cut off
# exactly the way the PDF ones were.
EXCEL_MIN_COLUMN_WIDTH = 10.0
EXCEL_MAX_COLUMN_WIDTH = 34.0
EXCEL_COLUMN_PADDING = 2.0

# The auditor's own tally, filled in by hand at the branch. Written blank and
# banner-ed under "Sumeru", mirroring the yellow block on the PDF.
#
# These are part of the sheet by declaration. They used to arrive only from a
# reference workbook found at manual_converted/<filename> relative to the
# working directory, so whether the report had its audit block at all came
# down to where the process happened to be started from.
EXCEL_AUDIT_BLOCK_COLUMNS = [
    "Count of Ornament",
    "Gross Wt.",
    "Stone Wt",
    "Karat",
    "Purity%",
    "Net Weight",
    "Remarks",
]
EXCEL_AUDIT_BANNER = "Sumeru"

# pandas writes the header at this 0-based offset, leaving row 1 for the banner.
EXCEL_BANNER_STARTROW = 1
EXCEL_BANNER_ROW = 1
EXCEL_HEADER_ROW = 2

_YELLOW = "FFFFFF00"
# Pink on the data headings, matching the reference sheet. Change this one
# value if the shade is off.
_HEADER_PINK = "FFF4CCCC"
EXCEL_AUDIT_FILL = PatternFill("solid", fgColor=_YELLOW)
EXCEL_HEADER_FILL = PatternFill("solid", fgColor=_HEADER_PINK)

# Widths still sum to PRINTABLE_WIDTH, but the space is shared out so that
# every header fits on the lines it is written on. Several columns used to be
# narrower than their own heading — "Count of Ornament" was short by a
# fraction of a point and had been abbreviated to "Ornamen" to hide it. The
# slack came from the hand-filled audit block, which was far wider than its
# headings needed. test_arvog_service.py asserts both properties.
PDF_COLUMN_WIDTHS = [
    26.00,   # SR No.
    116.55,  # Customer Name
    58.00,   # Loan No.
    58.00,   # PACKET NUMBER
    52.00,   # Ornament No.
    62.00,   # Ornament Name
    38.00,   # Gross Wt.
    38.00,   # Stone Wt.
    40.00,   # Karat
    40.00,   # Net Wt.
    54.00,   # Count of Ornament
    72.00,   # Gross Wt.    (audit block)
    72.00,   # Stone Wt     (audit block)
    72.00,   # Net Weight   (audit block)
    62.00,   # Karat        (audit block)
    191.55,  # Remarks      (audit block)
]


# =========================================================
# ArvogService class
# =========================================================

class ArvogService:
    """Service for Arvog Bank PDF generation from Excel data."""

    name = "Arvog Bank"
    REQUIRED_COLUMNS = list(REQUIRED_COLUMNS)

    # --- Static helpers -----------------------------------------------

    @staticmethod
    def normalize_columns(cols):
        return [str(c).strip().lower() for c in cols]

    @staticmethod
    def format_value(value, kind: ColumnKind | None = None):
        """Render a cell as text, to the display rules of its column type."""
        return display_value(value, kind)

    @staticmethod
    def make_cell(value, style, kind: ColumnKind | None = None):
        text = ArvogService.format_value(value, kind)
        if not text:
            return ""
        escaped = html.escape(text)
        formatted = escaped.replace("\n", "<br/>")
        return Paragraph(formatted, style)

    # --- Detection ----------------------------------------------------

    def detect_raw_excel(self, excel_path: str) -> tuple:
        try:
            xls = pd.ExcelFile(excel_path)
            for sheet_name in xls.sheet_names:
                df_temp = pd.read_excel(excel_path, sheet_name=sheet_name, nrows=3, header=None)
                for r_idx in range(len(df_temp)):
                    row_vals = [str(x).strip().lower() for x in df_temp.iloc[r_idx] if pd.notna(x)]
                    if "jewellery1" in row_vals and "jewellery2" in row_vals:
                        return sheet_name, r_idx
        except Exception:
            pass
        return None, None

    def detect_tall_sheet(self, excel_path: str) -> tuple[str | None, int | None]:
        """Find the already-converted sheet, and which row its headings are on.

        The row is not always the first. A sheet we produce now carries the
        "Sumeru" banner above its headings; one produced before that banner
        existed does not, and both are in circulation with auditors.
        """
        xls = pd.ExcelFile(excel_path)
        for sheet_name in xls.sheet_names:
            try:
                rows = read_rows(excel_path, str(sheet_name), HEADER_SCAN_ROWS)
            except Exception:
                continue
            header_row = find_header_row(rows, self.REQUIRED_COLUMNS)
            if header_row is not None:
                return str(sheet_name), header_row
        return None, None

    def detect_valid_sheet(self, excel_path: str) -> str:
        sheet_name, _header_row = self.detect_tall_sheet(excel_path)
        if sheet_name is not None:
            return sheet_name

        raise Exception("No valid sheet found.")

    # --- Conversion ---------------------------------------------------

    def convert_raw_to_tall(
        self,
        excel_path: str,
        sheet_name: str,
        header_row: int,
        cluster_manager: str | None = None,
        log_func: Callable = logger.info,
        schema_reference: str | None = None,
    ) -> pd.DataFrame:
        """Explode a wide master sheet into one row per ornament.

        ``schema_reference`` optionally points at a workbook whose header row
        dictates the output columns. It is an explicit argument on purpose:
        this used to be an implicit probe for ``manual_converted/<filename>``
        relative to the current working directory, which made the same input
        file convert differently depending on where the process was started
        from — and never fired at all in the packaged app or the container,
        where that directory does not exist.
        """
        df_raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=header_row)
        df_raw.columns = [str(c).strip() for c in df_raw.columns]

        reference_headers = None
        if schema_reference:
            if os.path.exists(schema_reference):
                try:
                    df_ref = pd.read_excel(schema_reference, nrows=1)
                    reference_headers = [str(c).strip() for c in df_ref.columns]
                    log_func(f"Aligning schema with reference sheet: {schema_reference}")
                except Exception as e:
                    log_func(f"Could not read schema reference {schema_reference}: {e}")
            else:
                log_func(f"Schema reference not found, deriving columns from the file: {schema_reference}")

        if reference_headers is not None:
            tall_cols = reference_headers
        else:
            raw_cols_set = {str(c).strip() for c in df_raw.columns}

            beg_group = ["SR No.", "Branch", "Region", "Date", "Customer Name", "Loan No.", "Loan type", "Partner Name", "Customer ID"]
            beg_present = [c for c in beg_group if c in raw_cols_set]

            end_group = ["Loan Amount", "Auditor Name", "Appraiser Name", "Packets Location", "Cluster Manager", "Packets Number", "After audit packet number"]
            end_present = [c for c in end_group if c in raw_cols_set]

            jewellery_cols = [
                "Jewellery No.", "Jewellery1", "Gross Wt.", "Stone Wt.", "Net Wt.",
                "Karat", "Purity % %", "Net weight after Purity %"
            ]
            tall_cols = beg_present + jewellery_cols + end_present

        # Ornament columns are located by position, anchored on each
        # Jewellery{i} heading in the file's own header row. Going through
        # pandas' de-duplicated names instead would assume every ornament
        # occupies seven columns — true of the original master, false of one
        # rebuilt from a filled audit sheet, where the auditor's block travels
        # with each ornament and repeats "Gross Wt." and "Karat".
        raw_headers = read_header_row(excel_path, sheet_name, header_row)
        ornament_blocks = [b for b in map_ornaments(raw_headers) if b.name < len(df_raw.columns)]

        converted_rows = []

        for idx, row in df_raw.iterrows():
            if pd.isna(row.get("Loan No.")) and pd.isna(row.get("SR No.")):
                continue

            first_ornament_for_loan = True

            for block in ornament_blocks:
                i = block.number

                ornament_name = row.iloc[block.name]
                if pd.isna(ornament_name):
                    continue
                ornament_name_str = str(ornament_name).strip()
                if ornament_name_str in ("-", ""):
                    continue

                def _cell(attribute, _row=row, _block=block):
                    column = _block.data.get(attribute)
                    if column is None or column >= len(_row):
                        return None
                    return _row.iloc[column]

                gross_wt, stone_wt, net_wt, karat, purity, net_wt_purity = (
                    _cell(attribute) for attribute in DATA_ATTR_ORDER
                )

                if isinstance(karat, str):
                    karat = karat.strip()

                new_row = {}

                if first_ornament_for_loan:
                    for col in tall_cols:
                        if col not in ["Jewellery No.", "Jewellery1", "Gross Wt.", "Stone Wt.", "Net Wt.", "Karat", "Purity % %", "Net weight after Purity %"]:
                            new_row[col] = row.get(col)

                    if "Cluster Manager" in tall_cols and pd.isna(new_row.get("Cluster Manager")):
                        # An explicit argument wins; otherwise fall back to the
                        # standing manager configured for that region.
                        new_row["Cluster Manager"] = (
                            cluster_manager
                            or arvog_config.cluster_manager_for(row.get("Region"))
                        )

                    first_ornament_for_loan = False
                else:
                    for col in tall_cols:
                        if col not in ["Jewellery No.", "Jewellery1", "Gross Wt.", "Stone Wt.", "Net Wt.", "Karat", "Purity % %", "Net weight after Purity %"]:
                            new_row[col] = None

                new_row["Jewellery No."] = f"Jewellery{i}"
                new_row["Jewellery1"] = ornament_name_str
                new_row["Gross Wt."] = gross_wt
                new_row["Stone Wt."] = stone_wt
                new_row["Net Wt."] = net_wt
                new_row["Karat"] = karat
                new_row["Purity % %"] = purity
                new_row["Net weight after Purity %"] = net_wt_purity

                ordered_row = {col: new_row.get(col) for col in tall_cols}
                converted_rows.append(ordered_row)

        return pd.DataFrame(converted_rows)

    # --- Formatting ---------------------------------------------------

    def append_audit_block(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add the blank hand-fill columns that close the report.

        Two of the headings ("Gross Wt.", "Karat") repeat ones already in the
        jewellery block, so this cannot go through the per-row dicts that build
        the tall frame — a dict would collapse the repeats and the block would
        come out short. Concatenating the columns keeps both.
        """
        if self._audit_block_span([str(c) for c in df.columns]) is not None:
            return df  # already present, e.g. re-processing a converted sheet
        blanks = pd.DataFrame(
            [[None] * len(EXCEL_AUDIT_BLOCK_COLUMNS) for _ in range(len(df))],
            columns=EXCEL_AUDIT_BLOCK_COLUMNS,
            index=df.index,
        )
        return pd.concat([df, blanks], axis=1)

    @staticmethod
    def _audit_block_span(headers: list) -> tuple[int, int] | None:
        """1-based inclusive column span of the audit block, or None."""
        size = len(EXCEL_AUDIT_BLOCK_COLUMNS)
        if len(headers) < size:
            return None
        tail = [str(h) if h is not None else "" for h in headers[-size:]]
        if tail != EXCEL_AUDIT_BLOCK_COLUMNS:
            return None
        return len(headers) - size + 1, len(headers)

    def write_converted_excel(self, df: pd.DataFrame, excel_path: str) -> None:
        """Save the tall sheet: data, the auditor's blank block, and the banner."""
        sheet_df = self.append_audit_block(df)
        sheet_df.to_excel(excel_path, index=False, startrow=EXCEL_BANNER_STARTROW)
        self.apply_excel_formatting(excel_path, header_row=EXCEL_HEADER_ROW)

    def apply_excel_formatting(self, excel_path: str, header_row: int = 1) -> None:
        wb = openpyxl.load_workbook(excel_path)
        ws = wb.active

        if ws is None:
            # No active sheet – try the first sheet, or bail out
            if wb.sheetnames:
                ws = wb[wb.sheetnames[0]]
            else:
                logger.warning("Workbook %s has no sheets – skipping formatting", excel_path)
                return

        header_cells = ws[header_row]
        if not header_cells:
            logger.warning("Sheet has no rows – skipping formatting")
            return

        headers = [cell.value for cell in header_cells]
        audit_span = self._audit_block_span(headers)

        for cell in header_cells:
            cell.alignment = EXCEL_CELL_ALIGNMENT
            cell.border = EXCEL_CELL_BORDER
            in_audit_block = audit_span is not None and audit_span[0] <= cell.column <= audit_span[1]
            cell.fill = EXCEL_AUDIT_FILL if in_audit_block else EXCEL_HEADER_FILL

        if audit_span is not None and header_row > 1:
            self._write_audit_banner(ws, audit_span, header_row - 1)

        # One number format per column, chosen from the column's declared type
        # rather than from a hand-maintained list of header names. The previous
        # chain gave every text column an integer format ("0") and formatted
        # "After audit packet number" as a date.
        first_data_row = header_row + 1
        for col_idx, h in enumerate(headers):
            kind = kind_for(h)
            values = [ws.cell(row=r, column=col_idx + 1).value for r in range(first_data_row, ws.max_row + 1)]
            fmt = excel_format_for(kind, values if format_depends_on_values(kind) else ())

            for r, _value in enumerate(values, start=first_data_row):
                cell = ws.cell(row=r, column=col_idx + 1)
                cell.number_format = fmt
                cell.alignment = EXCEL_CELL_ALIGNMENT
                # Boxed even when empty: a blank cell inside the table still
                # belongs to the table.
                cell.border = EXCEL_CELL_BORDER

            ws.column_dimensions[get_column_letter(col_idx + 1)].width = self._column_width(h, values, kind)

        wb.save(excel_path)

    @staticmethod
    def _write_audit_banner(ws, audit_span: tuple[int, int], banner_row: int) -> None:
        """Put "Sumeru" across the top of the hand-filled block."""
        first_col, last_col = audit_span
        ws.merge_cells(start_row=banner_row, start_column=first_col, end_row=banner_row, end_column=last_col)
        for col in range(first_col, last_col + 1):
            cell = ws.cell(row=banner_row, column=col)
            cell.fill = EXCEL_AUDIT_FILL
            cell.border = EXCEL_CELL_BORDER
        banner = ws.cell(row=banner_row, column=first_col)
        banner.value = EXCEL_AUDIT_BANNER
        banner.alignment = EXCEL_CELL_ALIGNMENT

    @staticmethod
    def _column_width(header, values, kind: ColumnKind | None = None) -> float:
        """Width that shows the column's contents, and its heading once wrapped.

        Sized from what Excel will *display*, not from the stored value: a date
        is held as 2026-03-05 00:00:00 but shown as 05-Mar-26, and an amount
        held as 125000 is shown as 125,000.00.

        The heading counts in full. Nothing wraps, so the whole of "After audit
        packet number" has to fit on the one line it gets.
        """
        widest_value = max((len(display_value(v, kind)) for v in values), default=0)
        heading = len(" ".join(str(header or "").split()))
        needed = max(widest_value, heading) + EXCEL_COLUMN_PADDING
        return max(EXCEL_MIN_COLUMN_WIDTH, min(needed, EXCEL_MAX_COLUMN_WIDTH))

    # --- Data cleaning ------------------------------------------------

    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        df.columns = [str(c).strip() for c in df.columns]
        df = df.dropna(how="all")

        missing = [c for c in self.REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise Exception(f"Missing columns: {missing}")

        return df

    # --- PDF generation -----------------------------------------------

    def generate_pdf(self, branch_name: str, df: pd.DataFrame, output_path: str) -> None:
        doc = SimpleDocTemplate(
            output_path,
            pagesize=landscape(A3),
            leftMargin=PAGE_LEFT_MARGIN,
            rightMargin=PAGE_RIGHT_MARGIN,
            topMargin=PAGE_TOP_MARGIN,
            bottomMargin=PAGE_BOTTOM_MARGIN,
            title=os.path.basename(output_path),
            author="Audit Automation",
        )

        body_style = ParagraphStyle(
            'BodyStyle',
            fontName='Times-Bold',
            fontSize=8.19,
            leading=9.5,
            alignment=TA_CENTER,
            textColor=colors.black,
        )

        audit_block_width = len(PDF_HEADERS) - AUDIT_BLOCK_FIRST_COLUMN
        blank_audit_cells = [""] * audit_block_width

        table_data = []

        table_data.append(
            [f"Branch Name - {branch_name}"]
            + [""] * (AUDIT_BLOCK_FIRST_COLUMN - 1)
            + ["Sumeru"]
            + [""] * (audit_block_width - 1)
        )

        table_data.append(list(PDF_HEADERS))

        # Each cell is rendered by the type of its source column, so a weight
        # reads "2.00" whether the workbook stored 2, 2.0 or "2.000".
        cell_kinds = [kind_for(column) for column in PDF_DATA_COLUMNS]

        for _, row in df.iterrows():
            table_data.append([
                self.make_cell(row.get(column), body_style, kind)
                for column, kind in zip(PDF_DATA_COLUMNS, cell_kinds)
            ] + blank_audit_cells)

        row_heights = [BANNER_ROW_HEIGHT, HEADER_ROW_HEIGHT] + [DATA_ROW_HEIGHT] * len(df)

        table = Table(table_data, colWidths=list(PDF_COLUMN_WIDTHS), rowHeights=row_heights, repeatRows=2)

        first_audit = AUDIT_BLOCK_FIRST_COLUMN
        last_column = len(PDF_HEADERS) - 1

        style = TableStyle([
            ("FONTNAME", (0, 0), (-1, 1), HEADER_FONT),
            ("FONTSIZE", (0, 0), (-1, 1), HEADER_FONT_SIZE),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
            ("BACKGROUND", (first_audit, 0), (last_column, 0), colors.yellow),
            ("BACKGROUND", (first_audit, 1), (last_column, 1), colors.yellow),
            ("SPAN", (0, 0), (first_audit - 1, 0)),
            ("SPAN", (first_audit, 0), (last_column, 0)),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), CELL_HORIZONTAL_PADDING),
            ("RIGHTPADDING", (0, 0), (-1, -1), CELL_HORIZONTAL_PADDING),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ])

        table.setStyle(style)
        doc.build([table])

    # --- Main processing pipeline -------------------------------------

    def process_excel(
        self,
        input_excel: str,
        output_dir: str,
        cluster_manager: str | None = None,
        convert_only: bool = False,
        log_func: Callable = logger.info,
        output_format: str = "BOTH",
        schema_reference: str | None = None,
    ) -> None:
        os.makedirs(output_dir, exist_ok=True)

        log_func(f"Reading Excel: {input_excel}")

        if convert_only:
            output_format = "EXCEL ONLY"

        sheet_name, header_row = self.detect_raw_excel(input_excel)
        if sheet_name is not None:
            log_func(f"Detected Raw Wide-Format Bank Excel in sheet '{sheet_name}' (row {header_row}). Converting...")
            df = self.convert_raw_to_tall(
                input_excel, sheet_name, header_row,
                cluster_manager=cluster_manager, log_func=log_func,
                schema_reference=schema_reference,
            )
            # Normalise once, before anything is written, so the Excel and the
            # PDF are rendered from identical values.
            df = normalize_dataframe(df)
            if output_format in ("EXCEL ONLY", "BOTH"):
                base_name = os.path.basename(input_excel)
                converted_excel_path = os.path.join(output_dir, base_name)
                log_func(f"Saving converted Excel to: {converted_excel_path}")
                # The audit block goes only into the workbook. It repeats two
                # headings, which would make row.get("Gross Wt.") ambiguous for
                # the PDF, so the frame the PDF renders keeps single columns.
                self.write_converted_excel(df, converted_excel_path)
        else:
            sheet_name, tall_header_row = self.detect_tall_sheet(input_excel)
            if sheet_name is None:
                raise Exception("No valid sheet found.")
            log_func(f"Detected Converted Tall-Format Excel Sheet: {sheet_name}")
            df = normalize_dataframe(
                pd.read_excel(input_excel, sheet_name=sheet_name, header=tall_header_row or 0)
            )

        if output_format in ("PDF ONLY", "BOTH"):
            df = self.clean_dataframe(df)
            df["Branch"] = df["Branch"].ffill()
            grouped = df.groupby("Branch", sort=False)

            total = 0
            for branch, grp_df in grouped:
                branch_df = grp_df.reset_index(drop=True)
                branch_name = self.format_value(branch)
                safe_branch = branch_name.replace("/", "_")
                output_file = os.path.join(output_dir, f"{safe_branch}.pdf")
                log_func(f"Generating -> {output_file}")
                self.generate_pdf(branch_name=branch_name, df=branch_df, output_path=output_file)
                total += 1

            log_func(f"Done. Generated {total} PDFs.")
        log_func(f"Output Folder: {output_dir}")


# =========================================================
# Backward-compatible module-level wrappers
# =========================================================

_default_service = ArvogService()


def normalize_columns(cols):
    return ArvogService.normalize_columns(cols)


def format_value(value, kind=None):
    return ArvogService.format_value(value, kind)


def make_cell(value, style, kind=None):
    return ArvogService.make_cell(value, style, kind)


def detect_raw_excel(excel_path):
    return _default_service.detect_raw_excel(excel_path)


def detect_valid_sheet(excel_path):
    return _default_service.detect_valid_sheet(excel_path)


def detect_tall_sheet(excel_path):
    return _default_service.detect_tall_sheet(excel_path)


def convert_raw_to_tall(excel_path, sheet_name, header_row, cluster_manager=None, log_func=print, schema_reference=None):
    return _default_service.convert_raw_to_tall(
        excel_path, sheet_name, header_row,
        cluster_manager=cluster_manager, log_func=log_func,
        schema_reference=schema_reference,
    )


def apply_excel_formatting(excel_path):
    return _default_service.apply_excel_formatting(excel_path)


def clean_dataframe(df):
    return _default_service.clean_dataframe(df)


def generate_pdf(branch_name, df, output_path):
    return _default_service.generate_pdf(branch_name, df, output_path)


def process_excel(input_excel, output_dir, cluster_manager=None, convert_only=False, log_func=print, output_format="BOTH", schema_reference=None):
    return _default_service.process_excel(
        input_excel, output_dir,
        cluster_manager=cluster_manager, convert_only=convert_only, log_func=log_func,
        output_format=output_format, schema_reference=schema_reference,
    )


# =========================================================
# CLI
# =========================================================

def parse_args():
    parser = argparse.ArgumentParser(description="Generate branch-wise PDFs from Excel")
    parser.add_argument("input_file", help="Path to Excel file")
    parser.add_argument("--output-dir", default="generated_pdfs", help="Output folder")
    parser.add_argument("--cluster-manager", default=None, help="Cluster Manager name to populate")
    parser.add_argument("--convert-only", action="store_true", help="Only convert raw wide-format Excel to tall-format and do not generate PDFs")
    parser.add_argument("--schema-reference", default=None, help="Workbook whose header row defines the converted columns")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    process_excel(
        input_excel=args.input_file,
        output_dir=args.output_dir,
        cluster_manager=args.cluster_manager,
        convert_only=args.convert_only,
        schema_reference=args.schema_reference,
    )
