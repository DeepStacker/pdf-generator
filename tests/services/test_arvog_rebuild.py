"""Tests for folding a filled audit sheet back into the wide master layout."""

import openpyxl
import pytest

from audit_engine.services.arvog import ArvogService
from audit_engine.services.arvog_layout import AUDIT_BLOCK_COLUMNS, LEADING_COLUMNS, TRAILING_COLUMNS
from audit_engine.services.arvog_rebuild import (
    BANNER_ROW,
    FIRST_DATA_ROW,
    HEADER_ROW,
    RebuildError,
    rebuild_wide_workbook,
    remap_formula,
)

GROUP_WIDTH = 15


# ---------------------------------------------------------------------------
# Fixtures: a tall sheet exactly as the forward path produces one
# ---------------------------------------------------------------------------

def _wide_master(path: str, loans: list[int]) -> str:
    """A branch's wide master. `loans` gives each loan's ornament count."""
    headers = list(LEADING_COLUMNS)
    for i in range(1, max(loans) + 1):
        headers.append(f"Jewellery{i}")
        headers += ["Gross Wt.", "Stone Wt.", "Net Wt.", "Karat", "Purity % %",
                    "Net weight after Purity %"]
    headers += TRAILING_COLUMNS

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for loan, count in enumerate(loans, start=1):
        row = [loan, "Hanamkonda", "WARANGAL", "05/03/2026", f"Customer {loan}",
               f"LN{loan:04d}", "secured", "Finkurve", f"CID{loan}"]
        for i in range(1, max(loans) + 1):
            if i <= count:
                row += [f"Ornament {loan}-{i}", 10.0 + i, 0.1 * i, 9.0 + i, "22 K",
                        0.916, 8.0 + i]
            else:
                row += [None] * 7
        row += [100000 + loan, "Auditor", "Appraiser", "Vault", None,
                f"PKT{loan}", f"PKT{loan}"]
        ws.append(row)
    wb.save(path)
    return path


def _tall_sheet(tmp_path, loans: list[int]) -> str:
    """Run the forward path, so the fixture is a real produced sheet.

    The widest loan needs at least two ornaments: a master with only a
    "Jewellery1" column is not recognised as wide, since detection looks for
    "Jewellery1" and "Jewellery2" together.
    """
    src = _wide_master(str(tmp_path / "master.xlsx"), loans)
    out_dir = tmp_path / "forward"
    ArvogService().process_excel(
        input_excel=src, output_dir=str(out_dir),
        log_func=lambda m: None, output_format="EXCEL ONLY",
    )
    return str(out_dir / "master.xlsx")


def _fill_audit_block(path: str, *, formula: bool = False) -> str:
    """Stand in for the auditor working down the sheet at the branch."""
    wb = openpyxl.load_workbook(path)
    ws = wb.active
    headers = [c.value for c in ws[HEADER_ROW]]
    col = {h: i + 1 for i, h in enumerate(headers)}
    audit_start = len(headers) - len(AUDIT_BLOCK_COLUMNS) + 1

    for r in range(FIRST_DATA_ROW, ws.max_row + 1):
        ws.cell(row=r, column=col["Count of Ornament"]).value = r
        ws.cell(row=r, column=audit_start + 1).value = 5.0 + r   # their Gross Wt.
        ws.cell(row=r, column=audit_start + 2).value = 0.5       # their Stone Wt
        ws.cell(row=r, column=audit_start + 3).value = 22        # their Karat
        if formula:
            gross = openpyxl.utils.get_column_letter(audit_start + 1)
            stone = openpyxl.utils.get_column_letter(audit_start + 2)
            ws.cell(row=r, column=audit_start + 5).value = f"={gross}{r}-{stone}{r}"
        else:
            ws.cell(row=r, column=audit_start + 5).value = 4.5 + r
        ws.cell(row=r, column=col["Remarks"]).value = f"Checked row {r}"
    wb.save(path)
    return path


def _rebuild(tmp_path, loans: list[int], *, formula: bool = False):
    tall = _fill_audit_block(_tall_sheet(tmp_path, loans), formula=formula)
    out = str(tmp_path / "rebuilt.xlsx")
    result = rebuild_wide_workbook(tall, out)
    return openpyxl.load_workbook(out, data_only=False).active, result


def _headers(ws):
    return [c.value for c in ws[HEADER_ROW]]


# ---------------------------------------------------------------------------

class TestLayout:
    def test_width_is_nine_plus_fifteen_per_ornament_plus_seven(self, tmp_path):
        ws, result = _rebuild(tmp_path, [2, 1, 4])
        assert result["widest_loan"] == 4
        assert result["columns"] == 9 + 4 * GROUP_WIDTH + 7 == 76
        assert ws.max_column == 76

    def test_only_as_many_groups_as_the_biggest_loan_needs(self, tmp_path):
        _, result = _rebuild(tmp_path, [1, 2])
        assert result["widest_loan"] == 2
        assert result["columns"] == 9 + 2 * GROUP_WIDTH + 7

    def test_one_row_per_loan(self, tmp_path):
        ws, result = _rebuild(tmp_path, [2, 1, 4])
        assert result["loans"] == 3
        assert ws.max_row == FIRST_DATA_ROW + 2

    def test_the_repeating_group(self, tmp_path):
        ws, _ = _rebuild(tmp_path, [2])
        headers = _headers(ws)
        assert headers[9:9 + GROUP_WIDTH] == [
            "Jewellery No.", "Jewellery1", "Gross Wt.", "Stone Wt.", "Net Wt.",
            "Karat", "Purity % %", "Net weight after Purity %",
            "Count of Ornament", "Gross Wt.", "Stone Wt", "Karat", "Purity%",
            "Net Weight", "Remarks",
        ]

    def test_groups_are_numbered(self, tmp_path):
        ws, _ = _rebuild(tmp_path, [3])
        headers = _headers(ws)
        assert [headers[9 + g * GROUP_WIDTH + 1] for g in range(3)] == [
            "Jewellery1", "Jewellery2", "Jewellery3",
        ]

    def test_loan_columns_lead_and_trail(self, tmp_path):
        ws, _ = _rebuild(tmp_path, [2])
        headers = _headers(ws)
        assert headers[:9] == LEADING_COLUMNS
        assert headers[-7:] == TRAILING_COLUMNS

    def test_repeated_headings_survive(self, tmp_path):
        """'Gross Wt.' and 'Karat' appear on both sides of every group."""
        ws, _ = _rebuild(tmp_path, [2])
        headers = _headers(ws)
        assert headers.count("Gross Wt.") == 4  # 2 groups x (branch + auditor)
        assert headers.count("Karat") == 4


class TestValues:
    def test_each_ornament_lands_in_its_own_group(self, tmp_path):
        ws, _ = _rebuild(tmp_path, [3])
        headers = _headers(ws)
        for g in range(3):
            name = ws.cell(row=FIRST_DATA_ROW, column=9 + g * GROUP_WIDTH + 2).value
            assert name == f"Ornament 1-{g + 1}"
            gross = ws.cell(row=FIRST_DATA_ROW, column=9 + g * GROUP_WIDTH + 3).value
            assert gross == pytest.approx(10.0 + g + 1)
        assert headers  # guard against an empty sheet passing silently

    def test_the_audit_block_travels_with_its_ornament(self, tmp_path):
        """Ornament 3's remark must not end up in ornament 1's block."""
        ws, _ = _rebuild(tmp_path, [3])
        remarks = [
            ws.cell(row=FIRST_DATA_ROW, column=9 + g * GROUP_WIDTH + 15).value
            for g in range(3)
        ]
        assert remarks == ["Checked row 3", "Checked row 4", "Checked row 5"]

    def test_loan_columns_come_from_the_first_ornament_row(self, tmp_path):
        ws, _ = _rebuild(tmp_path, [3, 2])
        assert ws.cell(row=FIRST_DATA_ROW, column=5).value == "Customer 1"
        assert ws.cell(row=FIRST_DATA_ROW + 1, column=5).value == "Customer 2"
        # Loan Amount is the first trailing column.
        assert ws.cell(row=FIRST_DATA_ROW, column=ws.max_column - 6).value == 100001

    def test_unused_groups_are_blank(self, tmp_path):
        ws, _ = _rebuild(tmp_path, [4, 1])
        short_loan = FIRST_DATA_ROW + 1
        for g in range(1, 4):
            for offset in range(GROUP_WIDTH):
                column = 9 + g * GROUP_WIDTH + offset + 1
                assert ws.cell(row=short_loan, column=column).value is None

    def test_a_blank_audit_cell_stays_blank(self, tmp_path):
        """The sample leaves Purity% empty; it must not become 0."""
        ws, _ = _rebuild(tmp_path, [2])
        purity = ws.cell(row=FIRST_DATA_ROW, column=9 + 13).value
        assert purity is None


class TestFormulas:
    def test_a_same_row_formula_is_retargeted(self, tmp_path):
        ws, result = _rebuild(tmp_path, [2], formula=True)
        assert result["formulas_retargeted"] == 2
        assert result["formulas_replaced_with_values"] == 0
        # Group 1's Net Weight = its own Gross - its own Stone.
        assert ws.cell(row=FIRST_DATA_ROW, column=9 + 14).value == "=S3-T3"
        assert ws.cell(row=FIRST_DATA_ROW, column=9 + GROUP_WIDTH + 14).value == "=AH3-AI3"

    def test_remap_rewrites_column_and_row(self):
        # source columns 25,26 -> target 18,19; row 3 -> row 7
        assert remap_formula("=Z3-AA3", 3, 7, {25: 18, 26: 19}) == "=S7-T7"

    def test_remap_refuses_a_reference_it_cannot_place(self):
        assert remap_formula("=Z3-AA9", 3, 7, {25: 18, 26: 19}) is None
        assert remap_formula("=ZZ3", 3, 7, {25: 18}) is None

    def test_remap_ignores_non_formulas(self):
        assert remap_formula("plain text", 3, 7, {}) is None
        assert remap_formula(None, 3, 7, {}) is None

    def test_the_workbook_recalculates_on_open(self, tmp_path):
        """Retargeted formulas carry no cached result."""
        tall = _fill_audit_block(_tall_sheet(tmp_path, [2]), formula=True)
        out = str(tmp_path / "rebuilt.xlsx")
        rebuild_wide_workbook(tall, out)
        assert openpyxl.load_workbook(out).calculation.fullCalcOnLoad is True


class TestPresentation:
    def test_sumeru_banners_every_audit_block(self, tmp_path):
        ws, _ = _rebuild(tmp_path, [3])
        for g in range(3):
            column = 9 + g * GROUP_WIDTH + 9
            assert ws.cell(row=BANNER_ROW, column=column).value == "Sumeru"

    def test_each_banner_is_merged_across_its_seven_columns(self, tmp_path):
        ws, _ = _rebuild(tmp_path, [2])
        spans = {(r.min_col, r.max_col) for r in ws.merged_cells.ranges if r.min_row == BANNER_ROW}
        assert spans == {(18, 24), (33, 39)}

    def test_the_audit_headings_are_yellow_and_the_rest_are_not(self, tmp_path):
        from audit_engine.services.arvog import _YELLOW
        ws, _ = _rebuild(tmp_path, [2])
        assert ws.cell(row=HEADER_ROW, column=18).fill.fgColor.rgb == _YELLOW
        assert ws.cell(row=HEADER_ROW, column=1).fill.fgColor.rgb != _YELLOW

    def test_every_cell_is_centred_and_boxed(self, tmp_path):
        ws, _ = _rebuild(tmp_path, [2])
        for row in ws.iter_rows(min_row=HEADER_ROW, max_row=ws.max_row):
            for cell in row:
                assert cell.alignment.horizontal == "center"
                sides = (cell.border.left, cell.border.right, cell.border.top, cell.border.bottom)
                assert all(s.style for s in sides), f"{cell.coordinate} is not boxed"

    def test_number_formats_come_from_the_registry(self, tmp_path):
        ws, _ = _rebuild(tmp_path, [2])
        headers = _headers(ws)
        fmt = {h: ws.cell(row=FIRST_DATA_ROW, column=i + 1).number_format
               for i, h in enumerate(headers)}
        assert fmt["Customer Name"] == "@"
        assert fmt["Net weight after Purity %"] == "0.00"
        assert fmt["Count of Ornament"] == "0"
        assert fmt["Remarks"] == "@"


class TestRoundTrip:
    def test_the_rebuilt_file_reads_back_as_a_wide_master(self, tmp_path):
        """The reader must handle 15-column groups, not just the original 7."""
        ws, _ = _rebuild(tmp_path, [2, 3])
        out = str(tmp_path / "rebuilt.xlsx")
        service = ArvogService()
        sheet, header_row = service.detect_raw_excel(out)
        assert sheet is not None
        df = service.convert_raw_to_tall(out, sheet, header_row, log_func=lambda m: None)
        assert len(df) == 5
        assert df["Gross Wt."].tolist() == pytest.approx([11.0, 12.0, 11.0, 12.0, 13.0])
        assert df["Jewellery1"].tolist() == [
            "Ornament 1-1", "Ornament 1-2", "Ornament 2-1", "Ornament 2-2", "Ornament 2-3",
        ]


class TestGuards:
    def test_a_missing_file(self, tmp_path):
        with pytest.raises(RebuildError, match="File not found"):
            rebuild_wide_workbook(str(tmp_path / "nope.xlsx"))

    def test_a_workbook_that_is_not_an_audit_sheet(self, tmp_path):
        path = str(tmp_path / "other.xlsx")
        wb = openpyxl.Workbook()
        wb.active.append(["Some", "Unrelated", "Columns"])
        wb.save(path)
        with pytest.raises(RebuildError, match="does not look like a converted audit sheet"):
            rebuild_wide_workbook(path)

    def test_a_sheet_with_headings_but_no_rows(self, tmp_path):
        tall = _tall_sheet(tmp_path, [2])
        wb = openpyxl.load_workbook(tall)
        ws = wb.active
        ws.delete_rows(FIRST_DATA_ROW, ws.max_row)
        wb.save(tall)
        with pytest.raises(RebuildError, match="no data rows"):
            rebuild_wide_workbook(tall)

    def test_the_default_output_sits_beside_the_source(self, tmp_path):
        tall = _fill_audit_block(_tall_sheet(tmp_path, [2]))
        result = rebuild_wide_workbook(tall)
        assert result["output_path"].endswith("_master.xlsx")
        assert result["output_bytes"] > 0

    def test_progress_is_reported(self, tmp_path):
        tall = _fill_audit_block(_tall_sheet(tmp_path, [2]))
        seen = []
        rebuild_wide_workbook(tall, str(tmp_path / "o.xlsx"), on_progress=lambda p, m: seen.append(p))
        assert seen and seen[-1] == 100.0
