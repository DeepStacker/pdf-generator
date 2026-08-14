"""Shared test fixtures and configuration."""

import os
import sys

# Ensure src/ is on the path so we import the package under src/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


import pytest


@pytest.fixture(autouse=True)
def _mock_dialogs(monkeypatch):
    import audit_engine.utils.dialogs
    import audit_engine.web.handlers

    monkeypatch.setattr(audit_engine.utils.dialogs, "ask_file_dialog", lambda: "")
    monkeypatch.setattr(audit_engine.utils.dialogs, "ask_files_dialog", lambda: [])
    monkeypatch.setattr(audit_engine.utils.dialogs, "ask_directory_dialog", lambda: "")

    monkeypatch.setattr(audit_engine.web.handlers, "ask_file_dialog", lambda: "")
    monkeypatch.setattr(audit_engine.web.handlers, "ask_files_dialog", lambda: [])
    monkeypatch.setattr(audit_engine.web.handlers, "ask_directory_dialog", lambda: "")



