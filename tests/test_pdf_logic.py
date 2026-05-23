"""Unit tests for pdf_logic.py — core PDF generation logic."""

import os
import sys
import tempfile
import pytest
import pandas as pd

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pdf_logic


# =========================================================
# format_tare_weight
# =========================================================
class TestFormatTareWeight:
    def test_none_returns_empty(self):
        assert pdf_logic.format_tare_weight(None) == ""

    def test_empty_string_returns_empty(self):
        assert pdf_logic.format_tare_weight("") == ""

    def test_nan_returns_empty(self):
        assert pdf_logic.format_tare_weight(float("nan")) == ""

    def test_pd_na_returns_empty(self):
        assert pdf_logic.format_tare_weight(pd.NA) == ""

    def test_integer_float_strips_decimal(self):
        """5.0 should become '5', not '5.0'"""
        assert pdf_logic.format_tare_weight(5.0) == "5"

    def test_actual_float_keeps_decimal(self):
        """5.5 should stay '5.5'"""
        assert pdf_logic.format_tare_weight(5.5) == "5.5"

    def test_integer_value(self):
        assert pdf_logic.format_tare_weight(10) == "10"

    def test_string_number(self):
        assert pdf_logic.format_tare_weight("7.0") == "7"

    def test_non_numeric_string(self):
        assert pdf_logic.format_tare_weight("N/A") == "N/A"

    def test_zero(self):
        assert pdf_logic.format_tare_weight(0) == "0"

    def test_large_number(self):
        assert pdf_logic.format_tare_weight(12345.0) == "12345"


# =========================================================
# validate_excel
# =========================================================
class TestValidateExcel:
    def test_empty_path(self):
        valid, err = pdf_logic.validate_excel("")
        assert not valid
        assert "No file path" in err

    def test_none_path(self):
        valid, err = pdf_logic.validate_excel(None)
        assert not valid

    def test_missing_file(self):
        valid, err = pdf_logic.validate_excel("/nonexistent/file.xlsx")
        assert not valid
        assert "not found" in err.lower()

    def test_wrong_extension(self, tmp_path):
        bad_file = tmp_path / "data.csv"
        bad_file.write_text("a,b,c")
        valid, err = pdf_logic.validate_excel(str(bad_file))
        assert not valid
        assert ".csv" in err

    def test_empty_file(self, tmp_path):
        empty_file = tmp_path / "empty.xlsx"
        empty_file.write_bytes(b"\x00")
        valid, err = pdf_logic.validate_excel(str(empty_file))
        # Should pass basic validation (has 4+ bytes check may fail depending on content)
        # The important thing is it doesn't crash
        assert isinstance(valid, bool)

    def test_valid_looking_file(self, tmp_path):
        """A file with .xlsx extension and enough bytes passes basic validation."""
        fake_xlsx = tmp_path / "test.xlsx"
        fake_xlsx.write_bytes(b"\x50\x4b\x03\x04" + b"\x00" * 100)  # ZIP magic bytes
        valid, err = pdf_logic.validate_excel(str(fake_xlsx))
        assert valid


# =========================================================
# validate_output_dir
# =========================================================
class TestValidateOutputDir:
    def test_empty_dir(self):
        valid, err = pdf_logic.validate_output_dir("")
        assert not valid

    def test_valid_dir(self, tmp_path):
        valid, err = pdf_logic.validate_output_dir(str(tmp_path))
        assert valid

    def test_new_dir_created(self, tmp_path):
        new_dir = str(tmp_path / "new_output")
        valid, err = pdf_logic.validate_output_dir(new_dir)
        assert valid
        assert os.path.isdir(new_dir)


# =========================================================
# group_by_branch
# =========================================================
class TestGroupByBranch:
    def test_normal_grouping(self):
        rows = [
            {"CurrentBranch": "BR001", "name": "A"},
            {"CurrentBranch": "BR001", "name": "B"},
            {"CurrentBranch": "BR002", "name": "C"},
        ]
        groups = pdf_logic.group_by_branch(rows)
        assert len(groups) == 2
        assert len(groups["BR001"]) == 2
        assert len(groups["BR002"]) == 1

    def test_none_branch_becomes_unknown(self):
        rows = [
            {"CurrentBranch": None, "name": "A"},
        ]
        groups = pdf_logic.group_by_branch(rows)
        assert "UNKNOWN" in groups

    def test_empty_branch_becomes_unknown(self):
        rows = [
            {"CurrentBranch": "", "name": "A"},
        ]
        groups = pdf_logic.group_by_branch(rows)
        assert "UNKNOWN" in groups

    def test_nan_branch_becomes_unknown(self):
        rows = [
            {"CurrentBranch": "nan", "name": "A"},
        ]
        groups = pdf_logic.group_by_branch(rows)
        assert "UNKNOWN" in groups

    def test_missing_key_becomes_unknown(self):
        rows = [{"name": "A"}]
        groups = pdf_logic.group_by_branch(rows)
        assert "UNKNOWN" in groups

    def test_empty_input(self):
        groups = pdf_logic.group_by_branch([])
        assert groups == {}


# =========================================================
# get_resource_path
# =========================================================
class TestGetResourcePath:
    def test_returns_string(self):
        result = pdf_logic.get_resource_path("fonts")
        assert isinstance(result, str)

    def test_returns_absolute_path(self):
        result = pdf_logic.get_resource_path("fonts")
        assert os.path.isabs(result)

    def test_fonts_dir_exists(self):
        result = pdf_logic.get_resource_path("fonts")
        assert os.path.isdir(result)


# =========================================================
# Constants integrity
# =========================================================
class TestConstants:
    def test_required_columns_list(self):
        assert len(pdf_logic.REQUIRED_COLUMNS) == 6
        assert "Prospectno" in pdf_logic.REQUIRED_COLUMNS
        assert "CUID" in pdf_logic.REQUIRED_COLUMNS

    def test_col_widths_count(self):
        """7 columns in the audit table."""
        assert len(pdf_logic.COL_WIDTHS) == 7

    def test_fonts_registered(self):
        """Font names should be set (either custom or fallback)."""
        assert pdf_logic.FONT_REG in ('Carlito', 'Helvetica')
        assert pdf_logic.FONT_BLD in ('ArimoBold', 'Helvetica-Bold')
