"""Tests for the ArvogService class API."""

import pandas as pd

from audit_engine.services.arvog import ArvogService


def test_service_can_be_instantiated():
    service = ArvogService()
    assert service is not None
    assert service.name == "Arvog Bank"


def test_static_normalize_columns():
    result = ArvogService.normalize_columns(["  Foo ", "BAR "])
    assert result == ["foo", "bar"]


def test_static_format_value():
    assert ArvogService.format_value(None) == ""
    assert ArvogService.format_value(pd.NA) == ""
    assert ArvogService.format_value(5.0) == "5"
    assert ArvogService.format_value(5.5) == "5.5"
    assert ArvogService.format_value("hello") == "hello"
    assert ArvogService.format_value("3.0") == "3"


def test_static_make_cell():
    from reportlab.lib.styles import ParagraphStyle
    style = ParagraphStyle("test", fontSize=10)
    cell = ArvogService.make_cell("hello", style)
    assert cell is not None
    assert "hello" in str(cell)
    empty = ArvogService.make_cell(None, style)
    assert empty == ""


def test_required_columns_present():
    assert len(ArvogService.REQUIRED_COLUMNS) == 11
    assert "SR No." in ArvogService.REQUIRED_COLUMNS
    assert "Branch" in ArvogService.REQUIRED_COLUMNS


def test_detect_raw_excel_nonexistent():
    service = ArvogService()
    sheet, row = service.detect_raw_excel("/nonexistent/file.xlsx")
    assert sheet is None
    assert row is None


def test_clean_dataframe_raises_on_missing(tmp_path):
    service = ArvogService()
    df = pd.DataFrame({"Foo": [1]})
    import pytest
    with pytest.raises(Exception, match="Missing columns"):
        service.clean_dataframe(df)


def test_service_process_excel_handles_missing_file(tmp_path):
    service = ArvogService()
    import pytest
    with pytest.raises(Exception):
        service.process_excel("/nonexistent/file.xlsx", str(tmp_path))
