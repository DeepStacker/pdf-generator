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

    def test_run_fails_when_already_running(self):
        consolidation_tracker.is_running = True
        res = handle_consolidate_run({"files": ["dummy.xlsx"], "month": "Feb'26"})
        assert res["success"] is False
        assert "already running" in res["error"]

    def test_run_fails_with_no_output_dir(self):
        res = handle_consolidate_run({"files": ["dummy.xlsx"], "month": "Feb'26", "output_dir": ""})
        assert res["success"] is False
        assert "output directory" in res["error"].lower()

    def test_run_starts_successfully(self, monkeypatch):
        # We don't want to run the actual background worker thread since it copies real files,
        # so we monkeypatch/mock the threading.Thread start.
        started_thread = False
        def mock_start(self_thread):
            nonlocal started_thread
            started_thread = True

        import threading
        monkeypatch.setattr(threading.Thread, "start", mock_start)

        res = handle_consolidate_run({"files": ["dummy.xlsx"], "month": "Feb'26", "output_dir": "/tmp"})
        assert res["success"] is True
        assert started_thread is True
        assert consolidation_tracker.is_running is True
        assert "Executing" in consolidation_tracker.progress_text
