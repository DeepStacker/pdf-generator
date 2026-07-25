"""Unit tests for the Excel Consolidation handlers and tracking."""

import os
import tempfile
import pytest
from pathlib import Path
from audit_engine.web.handlers import (
    handle_consolidate_run,
    handle_consolidate_progress,
    consolidation_tracker
)

class TestConsolidationHandlers:
    @pytest.fixture(autouse=True)
    def _reset_tracker(self):
        consolidation_tracker.is_running = False
        consolidation_tracker.progress_text = "Ready. Ingest raw spreadsheets."
        consolidation_tracker.exit_code = 0
        consolidation_tracker.summary = {}
        consolidation_tracker.error_msg = ""

    def test_progress_initial_state(self):
        res = handle_consolidate_progress()
        assert res["is_running"] is False
        assert "Ready" in res["progress_text"]
        assert res["exit_code"] == 0
        assert isinstance(res["summary"], dict)

    def test_run_fails_with_no_files(self):
        res = handle_consolidate_run({"files": [], "month": "Feb'26"})
        assert res["success"] is False
        assert "No source files selected" in res["error"]

    def test_run_fails_with_invalid_files(self):
        res = handle_consolidate_run({"files": ["non_existent_file.xlsx"], "month": "Feb'26"})
        assert res["success"] is False
        assert "No valid source files" in res["error"]

    def test_run_executes_successfully_with_valid_files(self, tmp_path):
        source_dir = Path(__file__).resolve().parent.parent / "src" / "audit_engine" / "consolidator" / "source_files"
        if not source_dir.exists():
            pytest.skip("source_files directory not found")

        source_files = [str(p) for p in source_dir.glob("*.xlsx") if not p.name.startswith(".")]
        if not source_files:
            pytest.skip("No source files available for testing")

        res = handle_consolidate_run({
            "files": source_files[:2],
            "month": "Mar'26",
            "output_dir": str(tmp_path)
        })
        assert res["success"] is True
        assert "summary" in res
        assert os.path.exists(res["output_path"])
