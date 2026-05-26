"""Smoke tests for the Bottle application and handlers."""


import pytest

from audit_engine.app import create_app, shutdown, shutdown_requested
from audit_engine.database import init_db
from audit_engine.tasks.workers import cancel_event, global_tracker
from audit_engine.web.handlers import (
    handle_browse_file,
    handle_browse_files,
    handle_browse_folder,
    handle_cancel,
    handle_config_save,
    handle_dashboard,
    handle_history,
    handle_history_clear,
    handle_open,
    handle_progress,
    handle_recent_clear,
    handle_run,
    handle_stats,
    handle_update_check,
    handle_update_install,
    handle_update_progress,
)


@pytest.fixture(autouse=True)
def _init_db():
    init_db()


class TestAppFactory:
    def test_create_app_returns_bottle_app(self):
        from audit_engine.lib.bottle import Bottle
        app = create_app(register_routes=False)
        assert isinstance(app, Bottle)

    def test_create_app_no_routes(self):
        app = create_app(register_routes=False)
        assert len(app.routes) == 0

    def test_create_app_with_routes(self):
        app = create_app(register_routes=True)
        assert len(app.routes) > 0


class TestShutdown:
    def test_shutdown_signal(self):
        from audit_engine.app import _shutdown_event
        initial = shutdown_requested()
        _shutdown_event.clear()
        assert shutdown_requested() is False
        shutdown()
        assert shutdown_requested() is True
        _shutdown_event.clear()
        if initial:
            shutdown()

    def test_shutdown_requested_initial(self):
        from audit_engine.app import _shutdown_event
        was = _shutdown_event.is_set()
        _shutdown_event.clear()
        assert shutdown_requested() is False
        if was:
            shutdown()


class TestUILoader:
    def test_get_html_returns_string(self):
        from audit_engine.ui import get_html
        html = get_html("1.0.0")
        assert isinstance(html, str)
        assert "1.0.0" in html

    def test_get_html_has_version_tag(self):
        from audit_engine.ui import get_html
        html = get_html("5.2.217")
        assert "5.2.217" in html
        assert "{{VERSION}}" not in html


class TestHandleDashboard:
    def test_dashboard_returns_all_keys(self):
        data = handle_dashboard()
        assert isinstance(data, dict)
        assert "bank" in data
        assert "total_sessions" in data
        assert "total_pdfs" in data
        assert "db_path" in data
        assert "log_path" in data
        assert "recent_files" in data
        assert "last_run" in data

    def test_dashboard_bank_is_string(self):
        data = handle_dashboard()
        assert isinstance(data["bank"], str)
        assert len(data["bank"]) > 0


class TestHandleProgress:
    def test_progress_initial(self):
        snap = handle_progress()
        assert snap["pct"] == 0.0
        assert snap["is_running"] is False

    def test_progress_after_update(self):
        global_tracker.reset()
        global_tracker.update_pct(50.0, "Test")
        snap = handle_progress()
        assert snap["pct"] == 50.0
        assert snap["active_branch"] == "Test"
        global_tracker.is_running = False
        global_tracker.reset()


class TestHandleCancel:
    def test_cancel_sets_event(self):
        cancel_event.clear()
        global_tracker.cancel_requested = False
        result = handle_cancel()
        assert result == {"success": True}
        assert cancel_event.is_set() is True

    def test_cancel_sets_tracker_flag(self):
        global_tracker.cancel_requested = False
        cancel_event.clear()
        handle_cancel()
        assert global_tracker.cancel_requested is True
        global_tracker.cancel_requested = False


class TestHandleRun:
    @pytest.fixture(autouse=True)
    def _reset_tracker(self):
        global_tracker.is_running = False
        cancel_event.clear()

    def test_run_already_running(self):
        global_tracker.reset()
        result = handle_run({"bank": "IDFC", "filepath": "/tmp/test.xlsx", "out_path": "/tmp"})
        assert result["success"] is False
        assert "already active" in result["error"]
        global_tracker.is_running = False
        global_tracker.reset()

    def test_run_missing_filepath(self):
        result = handle_run({"bank": "IDFC", "filepath": "", "out_path": "/tmp"})
        assert result["success"] is False
        assert "missing" in result["error"].lower() or "File" in result["error"]

    def test_run_invalid_out_path(self):
        result = handle_run({"bank": "IDFC", "filepath": "/tmp/test.xlsx", "out_path": ""})
        assert result["success"] is False

    def test_run_nonexistent_file(self):
        result = handle_run({"bank": "IDFC", "filepath": "/nonexistent/file.xlsx", "out_path": "/tmp"})
        assert result["success"] is False

    def test_run_list_empty(self):
        result = handle_run({"bank": "IDFC", "filepath": [], "out_path": "/tmp"})
        assert result["success"] is False

    def test_run_invalid_filepath_type(self):
        result = handle_run({"bank": "IDFC", "filepath": 123, "out_path": "/tmp"})
        assert result["success"] is False


class TestHandleHistory:
    def test_history_returns_list(self):
        result = handle_history()
        assert isinstance(result, list)

    def test_history_with_search(self):
        result = handle_history(search="test")
        assert isinstance(result, list)


class TestHandleHistoryClear:
    def test_history_clear(self):
        result = handle_history_clear()
        assert result == {"success": True}


class TestHandleRecentClear:
    def test_recent_clear(self):
        result = handle_recent_clear()
        assert result == {"success": True}


class TestHandleStats:
    def test_stats_returns_keys(self):
        data = handle_stats()
        assert "total_sessions" in data
        assert "total_pdfs" in data
        assert "total_excels" in data
        assert "distribution" in data
        assert "trend" in data


class TestHandleConfigSave:
    def test_save_valid_key(self):
        result = handle_config_save({"key": "bank", "value": "IDFC First Bank"})
        assert result["success"] is True

    def test_save_invalid_key(self):
        result = handle_config_save({"key": "invalid_key", "value": "x"})
        assert result["success"] is False
        assert "Unknown" in result["error"]

    def test_save_without_key(self):
        result = handle_config_save({"value": "x"})
        assert result["success"] is False


class TestHandleOpen:
    def test_open_nonexistent_path(self):
        result = handle_open({"path": "/nonexistent/path"})
        assert result == {"success": True}

    def test_open_empty_path(self):
        result = handle_open({"path": ""})
        assert result == {"success": True}


class TestHandleUpdate:
    def test_update_check_returns_dict(self):
        result = handle_update_check()
        assert isinstance(result, dict)

    def test_update_install_no_staged(self):
        result = handle_update_install()
        assert result["success"] is False

    def test_update_progress_returns_dict(self):
        result = handle_update_progress()
        assert "pct" in result
        assert "is_downloading" in result


class TestHandleBrowse:
    def test_handle_browse_file(self):
        result = handle_browse_file()
        assert "path" in result

    def test_handle_browse_files(self):
        result = handle_browse_files()
        assert "paths" in result

    def test_handle_browse_folder(self):
        result = handle_browse_folder()
        assert "path" in result
