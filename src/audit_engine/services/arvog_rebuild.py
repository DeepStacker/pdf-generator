"""Fold a filled audit sheet back into the wide master layout.

The forward path explodes a branch's wide master into one row per ornament so
the auditor can work down it at the branch. This is the return leg: once the
auditor has filled in their block — the count, their own weights, the karat and
the remark — the sheet is folded back so that each loan is a single row again
and each ornament's findings sit beside the branch's own figures.

The audit block travels **with its ornament**, not with the loan. Ornament
three's remark ends up in ornament three's block, which is why this cannot be a
simple group-and-join.

Formulas are rewritten rather than copied. The auditor's ``Net Weight`` is
typically ``=Z3-AA3`` — their gross minus their stone, on the same row. Folding
moves that pair to different columns *and* a different row, so the text is
retargeted; where a formula refers to anything this cannot account for, the
value Excel last computed is written instead, so nothing is silently lost.
"""

import logging
import os
import re
from collections.abc import Callable
from typing import Any, Final

import openpyxl
from openpyxl.utils import get_column_letter

from audit_engine.services.arvog import (
    EXCEL_AUDIT_FILL,
    EXCEL_CELL_ALIGNMENT,
    EXCEL_CELL_BORDER,
    EXCEL_HEADER_FILL,
    ArvogService,
)
from audit_engine.services.arvog_columns import excel_format_for, is_blank, kind_for
from audit_engine.services.arvog_layout import (
    AUDIT_BANNER,
    AUDIT_BLOCK_COLUMNS,
    DATA_ATTR_ORDER,
    LEADING_COLUMNS,
    MAX_ORNAMENTS,
    TRAILING_COLUMNS,
    index_of,
    map_ornaments,
    read_header_row,
)

logger = logging.getLogger(__name__)


class RebuildError(Exception):
    """Raised with a message meant for the user to read verbatim."""


# The rebuilt sheet, like the one it came from: banner, headings, then data.
BANNER_ROW: Final[int] = 1
HEADER_ROW: Final[int] = 2
FIRST_DATA_ROW: Final[int] = 3

# The eight columns a branch records per ornament, in the order the master
# lays them out. The first is the ornament's name.
ORNAMENT_DATA_HEADERS: Final[list[str]] = [
    "Gross Wt.", "Stone Wt.", "Net Wt.", "Karat", "Purity % %",
    "Net weight after Purity %",
]

_CELL_REF_RE: Final[re.Pattern[str]] = re.compile(r"(\$?)([A-Z]{1,3})(\$?)(\d+)")


def remap_formula(
    formula: str,
    src_row: int,
    dst_row: int,
    column_map: dict[int, int],
) -> str | None:
    """Repoint a same-row formula at the cells it now sits beside.

    ``column_map`` is 0-based source column -> 0-based target column for the
    ornament being moved. Returns None when any reference falls outside that
    map, which is the caller's signal to fall back to the cached value rather
    than write a formula pointing at the wrong cell.

    A sibling of ``report_validator.retarget_formula``, which only has to shift
    rows; folding moves columns as well, and by different amounts per ornament.
    """
    if not isinstance(formula, str) or not formula.startswith("="):
        return None

    failed = False

    def _sub(match: re.Match) -> str:
        nonlocal failed
        dollar_col, col_letters, dollar_row, row_digits = match.groups()
        if int(row_digits) != src_row:
            # Points at another row entirely; folding cannot know where it went.
            failed = True
            return match.group(0)
        src_col = openpyxl.utils.column_index_from_string(col_letters) - 1
        dst_col = column_map.get(src_col)
        if dst_col is None:
            failed = True
            return match.group(0)
        return f"{dollar_col}{get_column_letter(dst_col + 1)}{dollar_row}{dst_row}"

    rewritten = _CELL_REF_RE.sub(_sub, formula)
    return None if failed else rewritten


def _loan_rows(rows: list[list[Any]], lead_columns: list[int]) -> list[list[list[Any]]]:
    """Split the data rows into loans.

    A row carrying any loan-level value starts a new loan; a row with all of
    them blank is another ornament of the loan above. That is exactly the
    invariant the forward conversion writes.
    """
    loans: list[list[list[Any]]] = []
    for row in rows:
        if all(is_blank(cell) for cell in row):
            continue
        starts_loan = any(
            column < len(row) and not is_blank(row[column]) for column in lead_columns
        )
        if starts_loan or not loans:
            loans.append([row])
        else:
            loans[-1].append(row)
    return loans


def _build_headers(lead: list[str], trail: list[str], ornaments: int) -> list[str]:
    headers = list(lead)
    for i in range(1, ornaments + 1):
        headers.append("Jewellery No.")
        headers.append(f"Jewellery{i}")
        headers.extend(ORNAMENT_DATA_HEADERS)
        headers.extend(AUDIT_BLOCK_COLUMNS)
    headers.extend(trail)
    return headers


def _audit_span(lead_count: int, ornament: int) -> tuple[int, int]:
    """0-based first and last column of one ornament's audit block."""
    group_start = lead_count + (ornament - 1) * 15
    first = group_start + 8
    return first, first + len(AUDIT_BLOCK_COLUMNS) - 1


def rebuild_wide_workbook(
    src_path: str,
    output_path: str | None = None,
    on_progress: Callable[[float, str], None] | None = None,
) -> dict:
    """Fold a filled audit sheet back into the wide master layout.

    Path in, path out, so the desktop bridge and the web server can both call
    it. Returns a JSON-serializable summary.
    """
    progress = on_progress or (lambda _pct, _msg: None)

    if not src_path or not os.path.exists(src_path):
        raise RebuildError(f"File not found: {src_path}")

    progress(5.0, "Reading the audit sheet...")

    service = ArvogService()
    try:
        sheet_name, header_row = service.detect_tall_sheet(src_path)
    except Exception as e:
        raise RebuildError(f"Could not open the workbook: {e}") from e

    if sheet_name is None:
        raise RebuildError(
            "This does not look like a converted audit sheet - no sheet has the "
            "expected headings (SR No., Customer Name, Jewellery No. and the rest)."
        )

    headers = read_header_row(src_path, sheet_name, header_row)
    blocks = map_ornaments(headers)
    if not blocks:
        raise RebuildError("No 'Jewellery1' column found, so there is nothing to fold.")
    block = blocks[0]

    # Emit the loan columns the source actually has, in the master's order —
    # the mirror of how the forward conversion picks its columns.
    lead_map = {h: index_of(headers, h) for h in LEADING_COLUMNS}
    trail_map = {h: index_of(headers, h) for h in TRAILING_COLUMNS}
    lead = [h for h in LEADING_COLUMNS if lead_map[h] is not None]
    trail = [h for h in TRAILING_COLUMNS if trail_map[h] is not None]
    lead_columns = [lead_map[h] for h in lead]
    trail_columns = [trail_map[h] for h in trail]

    progress(20.0, "Grouping ornaments into loans...")

    values_wb = openpyxl.load_workbook(src_path, data_only=True)
    formula_wb = openpyxl.load_workbook(src_path, data_only=False)
    try:
        values_ws = values_wb[sheet_name]
        formula_ws = formula_wb[sheet_name]

        first_row = header_row + 2  # 1-based, past the header
        raw_rows = [
            list(row) for row in formula_ws.iter_rows(min_row=first_row, values_only=True)
        ]
        cached_rows = [
            list(row) for row in values_ws.iter_rows(min_row=first_row, values_only=True)
        ]
    finally:
        values_wb.close()
        formula_wb.close()

    loans_rows = _loan_rows(raw_rows, lead_columns)
    if not loans_rows:
        raise RebuildError("The sheet has headings but no data rows.")

    # Row indexes are needed to retarget formulas, so track where each row sat.
    row_number: dict[int, int] = {id(row): first_row + n for n, row in enumerate(raw_rows)}
    cached_by_number = {first_row + n: row for n, row in enumerate(cached_rows)}

    over_cap = [len(rows) for rows in loans_rows if len(rows) > MAX_ORNAMENTS]
    if over_cap:
        logger.warning(
            "%d loan(s) carry more than %d ornaments; the extras are dropped",
            len(over_cap), MAX_ORNAMENTS,
        )

    widest = min(max(len(rows) for rows in loans_rows), MAX_ORNAMENTS)
    out_headers = _build_headers(lead, trail, widest)
    lead_count = len(lead)

    progress(45.0, f"Folding {len(loans_rows)} loan(s) into {widest} ornament group(s)...")

    # Ornament attributes in the order they appear in a group, paired with the
    # source column each is read from.
    data_sources = [block.data.get(attribute) for attribute in DATA_ATTR_ORDER]
    audit_sources = [block.audit.get(heading) for heading in AUDIT_BLOCK_COLUMNS]

    out_rows: list[list[Any]] = []
    formulas_kept = 0
    formulas_replaced = 0

    for loan_index, ornament_rows in enumerate(loans_rows):
        dst_row = FIRST_DATA_ROW + loan_index
        first = ornament_rows[0]
        row_out: list[Any] = [
            first[c] if c < len(first) else None for c in lead_columns
        ]

        for ornament, source_row in enumerate(ornament_rows[:MAX_ORNAMENTS], start=1):
            src_row = row_number[id(source_row)]
            group_start = lead_count + (ornament - 1) * 15

            # Where each source cell of this ornament ends up, for formulas.
            column_map: dict[int, int] = {}
            for offset, src_col in enumerate(data_sources):
                if src_col is not None:
                    column_map[src_col] = group_start + 2 + offset
            for offset, src_col in enumerate(audit_sources):
                if src_col is not None:
                    column_map[src_col] = group_start + 8 + offset

            def _value(src_col, _row=source_row, _src=src_row, _dst=dst_row, _map=column_map):
                nonlocal formulas_kept, formulas_replaced
                if src_col is None or src_col >= len(_row):
                    return None
                raw = _row[src_col]
                if isinstance(raw, str) and raw.startswith("="):
                    rewritten = remap_formula(raw, _src, _dst, _map)
                    if rewritten is not None:
                        formulas_kept += 1
                        return rewritten
                    formulas_replaced += 1
                    cached = cached_by_number.get(_src)
                    return cached[src_col] if cached and src_col < len(cached) else None
                return raw

            row_out.append(f"Jewellery{ornament}")
            row_out.append(_value(block.name))
            row_out.extend(_value(c) for c in data_sources)
            row_out.extend(_value(c) for c in audit_sources)

        # Pad the groups this loan does not use, so every row is the same width.
        row_out.extend([None] * ((widest - min(len(ornament_rows), MAX_ORNAMENTS)) * 15))
        row_out.extend(first[c] if c < len(first) else None for c in trail_columns)
        out_rows.append(row_out)

    progress(70.0, "Writing the master sheet...")

    if not output_path:
        stem, ext = os.path.splitext(src_path)
        output_path = f"{stem}_master{ext or '.xlsx'}"

    _write_workbook(output_path, out_headers, out_rows, lead_count, widest)

    progress(100.0, "Done.")

    total_ornaments = sum(min(len(r), MAX_ORNAMENTS) for r in loans_rows)
    return {
        "output_path": output_path,
        "output_name": os.path.basename(output_path),
        "source_name": os.path.basename(src_path),
        "sheet_name": sheet_name,
        "loans": len(loans_rows),
        "ornaments": total_ornaments,
        "widest_loan": widest,
        "columns": len(out_headers),
        "audit_columns_found": len(block.audit),
        "formulas_retargeted": formulas_kept,
        "formulas_replaced_with_values": formulas_replaced,
        "output_bytes": os.path.getsize(output_path),
    }


def _write_workbook(
    output_path: str,
    headers: list[str],
    rows: list[list[Any]],
    lead_count: int,
    ornaments: int,
) -> None:
    """Write the folded sheet, styled the way the forward output is."""
    wb = openpyxl.Workbook()
    ws = wb.active

    for column, heading in enumerate(headers, start=1):
        ws.cell(row=HEADER_ROW, column=column, value=heading)

    for offset, row in enumerate(rows):
        for column, value in enumerate(row, start=1):
            ws.cell(row=FIRST_DATA_ROW + offset, column=column, value=value)

    audit_columns: set[int] = set()
    for ornament in range(1, ornaments + 1):
        first, last = _audit_span(lead_count, ornament)
        audit_columns.update(range(first + 1, last + 2))  # 1-based
        ws.merge_cells(
            start_row=BANNER_ROW, start_column=first + 1,
            end_row=BANNER_ROW, end_column=last + 1,
        )
        banner = ws.cell(row=BANNER_ROW, column=first + 1, value=AUDIT_BANNER)
        banner.alignment = EXCEL_CELL_ALIGNMENT
        for column in range(first + 1, last + 2):
            cell = ws.cell(row=BANNER_ROW, column=column)
            cell.fill = EXCEL_AUDIT_FILL
            cell.border = EXCEL_CELL_BORDER

    last_row = FIRST_DATA_ROW + len(rows) - 1
    for column, heading in enumerate(headers, start=1):
        head = ws.cell(row=HEADER_ROW, column=column)
        head.alignment = EXCEL_CELL_ALIGNMENT
        head.border = EXCEL_CELL_BORDER
        head.fill = EXCEL_AUDIT_FILL if column in audit_columns else EXCEL_HEADER_FILL

        kind = kind_for(heading)
        column_values = [ws.cell(row=r, column=column).value for r in range(FIRST_DATA_ROW, last_row + 1)]
        number_format = excel_format_for(kind, column_values)

        for r in range(FIRST_DATA_ROW, last_row + 1):
            cell = ws.cell(row=r, column=column)
            cell.number_format = number_format
            cell.alignment = EXCEL_CELL_ALIGNMENT
            cell.border = EXCEL_CELL_BORDER

        ws.column_dimensions[get_column_letter(column)].width = ArvogService._column_width(
            heading, column_values, kind,
        )

    # The retargeted formulas have no cached result, so Excel must compute them
    # when the file is opened.
    wb.calculation.fullCalcOnLoad = True
    wb.save(output_path)
