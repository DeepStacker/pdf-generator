"""Tests for the Equitas audit logic service."""

from audit_engine.services import equitas as equitas_logic


def test_clean_text():
    assert equitas_logic.clean_text("  hello  ") == "hello"


def test_safe_float_numeric():
    assert equitas_logic.safe_float_numeric("123.45") == 123.45


def test_safe_float():
    assert equitas_logic.safe_float("abc") == "abc"
    assert equitas_logic.safe_float("123.456") == "123.456"


def test_base_sheet_name():
    assert equitas_logic.base_sheet_name("Sheet1") == "sheet1"


def test_format_3():
    assert equitas_logic.format_3(123.45678) == "123.457"
    assert equitas_logic.format_3("abc") == "0.000"
