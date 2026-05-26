"""Tests for the EquitasService class API."""

import pandas as pd

from audit_engine.services.equitas import EquitasService


def test_service_can_be_instantiated():
    service = EquitasService()
    assert service is not None
    assert service.name == "Equitas Small Finance Bank"


def test_static_clean_text():
    assert EquitasService.clean_text(None) == ""
    assert EquitasService.clean_text("") == ""
    assert EquitasService.clean_text("  hello  ") == "hello"
    assert EquitasService.clean_text("helloWorld") == "hello World"
    assert EquitasService.clean_text(pd.NA) == ""


def test_static_safe_value():
    assert EquitasService.safe_value(None) == ""
    assert EquitasService.safe_value(pd.NA) == ""
    assert EquitasService.safe_value("  abc  ") == "abc"
    assert EquitasService.safe_value(123) == "123"


def test_static_safe_float():
    assert EquitasService.safe_float(None) == ""
    assert EquitasService.safe_float("abc") == "abc"
    assert EquitasService.safe_float("123.456") == "123.456"
    assert EquitasService.safe_float(123.0) == "123"
    assert EquitasService.safe_float("") == ""
    assert EquitasService.safe_float("-") == ""


def test_static_safe_float_numeric():
    assert EquitasService.safe_float_numeric(None) == 0.0
    assert EquitasService.safe_float_numeric("123.45") == 123.45
    assert EquitasService.safe_float_numeric("abc") == 0.0
    assert EquitasService.safe_float_numeric("DIFF: 1.5") == 1.5


def test_static_format_date():
    assert EquitasService.format_date(None) == ""
    assert EquitasService.format_date(pd.NA) == ""
    d = EquitasService.format_date("2024-01-15")
    assert d == "15-01-2024"
    d2 = EquitasService.format_date(pd.Timestamp("2024-03-20"))
    assert d2 == "20-03-2024"


def test_static_base_sheet_name():
    assert EquitasService.base_sheet_name("Sheet1") == "sheet1"
    assert EquitasService.base_sheet_name("Branch_JSR") == "branch"
    assert EquitasService.base_sheet_name("Branch_JSR ") == "branch"
    assert EquitasService.base_sheet_name("branch_jsr") == "branch"


def test_static_format_3():
    assert EquitasService.format_3(123.45678) == "123.457"
    assert EquitasService.format_3(5) == "5.000"
    assert EquitasService.format_3("abc") == "0.000"


def test_static_sanitize_filename():
    name = EquitasService.sanitize_filename("foo/bar*baz")
    assert "/" not in name and "*" not in name
    assert "foo_bar_baz"


def test_static_generate_verification_id():
    vid = EquitasService.generate_verification_id()
    assert len(vid) == 10
    assert vid.isdigit()


def test_static_normalize_columns():
    import pandas as pd
    df = pd.DataFrame({" Name ": [1], "AGE ": [2]})
    ndf = EquitasService.normalize_columns(df)
    assert list(ndf.columns) == ["NAME", "AGE"]


def test_validate_stage1_invalid_path():
    service = EquitasService()
    valid, err = service.validate_stage1_file("")
    assert not valid
    assert "No file path" in err


def test_validate_stage1_none_path():
    service = EquitasService()
    valid, err = service.validate_stage1_file(None)
    assert not valid
    assert "No file path" in err


def test_validate_stage1_missing_file():
    service = EquitasService()
    valid, err = service.validate_stage1_file("/nonexistent/file.xlsx")
    assert not valid
    assert "File not found" in err


def test_validate_stage1_wrong_extension(tmp_path):
    service = EquitasService()
    txt = tmp_path / "data.txt"
    txt.write_text("not excel")
    valid, err = service.validate_stage1_file(str(txt))
    assert not valid
    assert "Invalid file type" in err


def test_validate_stage2_invalid_path():
    service = EquitasService()
    valid, err = service.validate_stage2_file("")
    assert not valid
    assert "No file path" in err


def test_instance_methods_delegate(monkeypatch):
    service = EquitasService()
    assert service.clean_text("  x  ") == "x"
    assert service.safe_float(5.0) == "5"
    assert service.safe_float_numeric("3.5") == 3.5
    assert service.base_sheet_name("Test_JSR") == "test"
    assert service.format_date("2024-06-01") == "01-06-2024"
    assert service.format_3(7) == "7.000"
    assert service.sanitize_filename("a/b") == "a_b"
