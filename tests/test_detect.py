"""Tests for bank auto-detection and Excel header preview."""

import openpyxl

from audit_engine.web.detect import BANK_PROFILES, detect_bank_from_file, peek_excel_data


def _make_excel(path: str, headers: list[str], data_rows: list[list] | None = None) -> str:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    if data_rows:
        for row in data_rows:
            ws.append(row)
    wb.save(path)
    return path


def test_bank_profiles_are_ordered_by_specificity():
    assert len(BANK_PROFILES) == 3
    assert BANK_PROFILES[0].name == "IDFC First Bank"
    assert BANK_PROFILES[1].name == "Equitas Small Finance Bank"
    assert BANK_PROFILES[2].name == "Arvog Bank"


def test_bank_profile_matches():
    profile = BANK_PROFILES[0]
    headers = {"prospectno", "cuid", "tare weight", "currentbranch"}
    assert profile.matches(headers)
    assert not profile.matches({"foo", "bar", "baz"})


def test_detect_idfc_bank(tmp_path):
    xlsx = _make_excel(str(tmp_path / "idfc.xlsx"),
                       ["ProspectNo", "CUID", "Tare Weight", "CurrentBranch", "State"])
    result = detect_bank_from_file(xlsx)
    assert result == "IDFC First Bank"


def test_detect_equitas_bank(tmp_path):
    xlsx = _make_excel(str(tmp_path / "equitas.xlsx"),
                       ["SVS_Loan_No", "SOLE_ID", "Branch_Name", "Loan No"])
    result = detect_bank_from_file(xlsx)
    assert result == "Equitas Small Finance Bank"


def test_detect_arvog_bank(tmp_path):
    xlsx = _make_excel(str(tmp_path / "arvog.xlsx"),
                       ["Jewellery1", "Jewellery2", "Gross Wt.", "Karat"])
    result = detect_bank_from_file(xlsx)
    assert result == "Arvog Bank"


def test_detect_nonexistent_file(tmp_path):
    result = detect_bank_from_file(str(tmp_path / "nonexistent.xlsx"))
    assert result is None


def test_detect_unknown_file(tmp_path):
    xlsx = _make_excel(str(tmp_path / "unknown.xlsx"),
                       ["Foo", "Bar", "Baz", "Quux"])
    result = detect_bank_from_file(xlsx)
    assert result is None


def test_peek_excel_returns_headers_and_preview(tmp_path):
    xlsx = _make_excel(
        str(tmp_path / "peek.xlsx"),
        ["A", "B", "C"],
        [["1", "2", "3"], ["4", "5", "6"]],
    )
    headers, rows = peek_excel_data(xlsx)
    assert headers == ["A", "B", "C"]
    assert len(rows) == 2


def test_peek_excel_nonexistent(tmp_path):
    headers, rows = peek_excel_data(str(tmp_path / "missing.xlsx"))
    assert headers == []
    assert rows == []
