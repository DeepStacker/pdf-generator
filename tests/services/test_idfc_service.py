"""Tests for the IDFCService class API."""

from audit_engine.services.idfc import IDFCService


def test_service_can_be_instantiated():
    service = IDFCService()
    assert service is not None
    assert service.font_reg in ("Carlito", "Helvetica")
    assert service.font_bld in ("ArimoBold", "Helvetica-Bold")


def test_service_validate_delegates():
    service = IDFCService()
    valid, err = service.validate("")
    assert not valid
    assert err == "No file path provided."


def test_service_validate_none():
    service = IDFCService()
    valid, err = service.validate(None)
    assert not valid
    assert err == "No file path provided."


def test_service_validate_missing_file():
    service = IDFCService()
    valid, err = service.validate("/nonexistent/file.xlsx")
    assert not valid
    assert "File not found" in err


def test_service_validate_wrong_extension(tmp_path):
    service = IDFCService()
    txt_file = tmp_path / "data.txt"
    txt_file.write_text("not an excel")
    valid, err = service.validate(str(txt_file))
    assert not valid
    assert "Invalid file type" in err


def test_service_validate_output_dir_empty():
    service = IDFCService()
    valid, err = service.validate_output_dir("")
    assert not valid
    assert err == "No output directory specified."


def test_service_format_tare_weight_none():
    service = IDFCService()
    assert service.format_tare_weight(None) == ""


def test_service_format_tare_weight_numeric():
    service = IDFCService()
    assert service.format_tare_weight(5.0) == "5"
    assert service.format_tare_weight(5.123) == "5.123"


def test_service_get_resource_path():
    path = IDFCService.get_resource_path("fonts")
    assert isinstance(path, str)
    assert path.startswith("/")


def test_service_group_by_branch():
    service = IDFCService()
    rows = [
        {"CurrentBranch": "A", "Prospectno": "1"},
        {"CurrentBranch": "A", "Prospectno": "2"},
        {"CurrentBranch": "B", "Prospectno": "3"},
    ]
    groups = service.group_by_branch(rows)
    assert len(groups) == 2
    assert len(groups["A"]) == 2
    assert len(groups["B"]) == 1


def test_service_group_by_branch_empty():
    service = IDFCService()
    groups = service.group_by_branch([])
    assert groups == {}
