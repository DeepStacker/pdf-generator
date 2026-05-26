"""Tests for the IDFC PDF generation service."""

import pandas as pd

from audit_engine.services import idfc as pdf_logic


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
        assert pdf_logic.format_tare_weight(5.0) == "5"

    def test_actual_float_keeps_decimal(self):
        assert pdf_logic.format_tare_weight(5.123) == "5.123"

    def test_integer_value(self):
        assert pdf_logic.format_tare_weight(5) == "5"

    def test_string_number(self):
        assert pdf_logic.format_tare_weight("23.45") == "23.45"

    def test_non_numeric_string(self):
        assert pdf_logic.format_tare_weight("N/A") == "N/A"

    def test_zero(self):
        assert pdf_logic.format_tare_weight(0) == "0"

    def test_large_number(self):
        assert pdf_logic.format_tare_weight(123456.789) == "123456.789"


class TestValidateExcel:
    def test_empty_path(self):
        valid, err = pdf_logic.validate_excel("")
        assert not valid
        assert err

    def test_none_path(self):
        valid, err = pdf_logic.validate_excel(None)
        assert not valid
        assert err

    def test_missing_file(self):
        valid, err = pdf_logic.validate_excel("/nonexistent/file.xlsx")
        assert not valid
        assert err

    def test_wrong_extension(self):
        valid, err = pdf_logic.validate_excel(__file__)  # .py file
        assert not valid
        assert err

    def test_empty_file(self):
        import os
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            p = f.name
        try:
            valid, err = pdf_logic.validate_excel(p)
            assert not valid
        finally:
            os.unlink(p)

    def test_valid_looking_file(self):
        valid, err = pdf_logic.validate_excel("/path/to/nonexistent/file.xlsx")
        assert not valid  # file doesn't exist


class TestValidateOutputDir:
    def test_empty_dir(self):
        valid, err = pdf_logic.validate_output_dir("")
        assert not valid
        assert err

    def test_valid_dir(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            valid, err = pdf_logic.validate_output_dir(d)
            assert valid
            assert not err

    def test_new_dir_created(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            new_dir = os.path.join(d, "new_output")
            valid, err = pdf_logic.validate_output_dir(new_dir)
            assert valid
            assert os.path.isdir(new_dir)


class TestGroupByBranch:
    def test_normal_grouping(self):
        rows = [
            {"CurrentBranch": "BranchA", "Prospectno": "1"},
            {"CurrentBranch": "BranchA", "Prospectno": "2"},
            {"CurrentBranch": "BranchB", "Prospectno": "3"},
        ]
        groups = pdf_logic.group_by_branch(rows)
        assert len(groups) == 2
        assert len(groups["BranchA"]) == 2

    def test_none_branch_becomes_unknown(self):
        rows = [{"foo": "bar"}]
        groups = pdf_logic.group_by_branch(rows)
        assert "UNKNOWN" in groups

    def test_empty_branch_becomes_unknown(self):
        rows = [{"CurrentBranchName": ""}]
        groups = pdf_logic.group_by_branch(rows)
        assert "UNKNOWN" in groups

    def test_nan_branch_becomes_unknown(self):
        rows = [{"CurrentBranchName": float("nan")}]
        groups = pdf_logic.group_by_branch(rows)
        assert "UNKNOWN" in groups

    def test_missing_key_becomes_unknown(self):
        rows = [{"SomeOtherKey": "value"}]
        groups = pdf_logic.group_by_branch(rows)
        assert "UNKNOWN" in groups

    def test_empty_input(self):
        groups = pdf_logic.group_by_branch([])
        assert groups == {}


class TestGetResourcePath:
    def test_returns_string(self):
        path = pdf_logic.get_resource_path("fonts")
        assert isinstance(path, str)

    def test_returns_absolute_path(self):
        path = pdf_logic.get_resource_path("fonts")
        assert path.startswith("/")

    def test_fonts_dir_exists(self):
        import os
        path = pdf_logic.get_resource_path("fonts")
        assert os.path.isdir(path)


class TestConstants:
    def test_required_columns_list(self):
        assert isinstance(pdf_logic.REQUIRED_COLUMNS, list)
        assert len(pdf_logic.REQUIRED_COLUMNS) > 0

    def test_col_widths_count(self):
        assert isinstance(pdf_logic.COL_WIDTHS, (list, tuple))
        assert len(pdf_logic.COL_WIDTHS) > 0

    def test_fonts_registered(self):
        pdf_logic.register_fonts()
        assert pdf_logic.FONT_REG is not None
        assert pdf_logic.FONT_BLD is not None
