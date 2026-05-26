"""Tests for domain data models."""

from audit_engine.domain.models import (
    BankProfile,
    GenerationRequest,
    GenerationResult,
    HistoryEntry,
    ProgressInfo,
    ValidationResult,
)


def test_generation_request_defaults():
    r = GenerationRequest(bank="IDFC", filepath="/tmp/test.xlsx", out_path="/tmp/out")
    assert r.bank == "IDFC"
    assert r.auto_open is True
    assert r.naming_pattern == "{branch}_{type}"
    assert r.audit_type == "POA"
    assert r.output_mode == "BOTH"
    assert r.column_mappings is None


def test_generation_request_list_filepath():
    r = GenerationRequest(bank="Eq", filepath=["a.xlsx", "b.xlsx"], out_path="/out")
    assert isinstance(r.filepath, list)
    assert len(r.filepath) == 2


def test_generation_result_success():
    r = GenerationResult(success=True, files_processed=3, items_generated=42)
    assert r.success is True
    assert r.files_processed == 3
    assert r.items_generated == 42
    assert r.error is None


def test_generation_result_failure():
    r = GenerationResult(success=False, error="disk full")
    assert r.success is False
    assert r.error == "disk full"


def test_progress_info_defaults():
    p = ProgressInfo()
    assert p.pct == 0.0
    assert p.active_branch == ""
    assert p.logs == []
    assert p.is_running is False
    assert p.summary is None
    assert p.cancel_requested is False


def test_progress_info_can_mutate():
    p = ProgressInfo()
    p.is_running = True
    p.pct = 50.0
    p.logs.append({"level": "INFO", "message": "test"})
    assert p.is_running is True
    assert p.pct == 50.0
    assert len(p.logs) == 1


def test_validation_result_defaults():
    v = ValidationResult(valid=True)
    assert v.valid is True
    assert v.error == ""
    assert v.detected_bank is None
    assert v.rows == 0
    assert v.branches == 0
    assert v.headers == []
    assert v.preview == []


def test_bank_profile_matches():
    profile = BankProfile("Test", frozenset({"a", "b", "c"}), 2)
    assert profile.matches({"a", "b", "x"}) is True
    assert profile.matches({"a", "x", "y"}) is False
    assert profile.matches(set()) is False


def test_bank_profile_empty_fingerprint():
    profile = BankProfile("Empty", frozenset(), 0)
    assert profile.matches({"anything"}) is True


def test_bank_profile_display_color():
    p = BankProfile("C", frozenset(), 0, display_color="#FF0000")
    assert p.display_color == "#FF0000"


def test_history_entry_defaults():
    h = HistoryEntry()
    assert h.id == 0
    assert h.timestamp == ""
    assert h.excel_name == ""
    assert h.pdf_count == 0


def test_history_entry_full():
    h = HistoryEntry(id=5, timestamp="2024-01-01", excel_name="report.xlsx", pdf_count=10, output_path="/out", audit_type="POA", full_path="/full/report.xlsx")
    assert h.id == 5
    assert h.pdf_count == 10
