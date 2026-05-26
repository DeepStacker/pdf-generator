"""Tests for the thread-safe ProgressTracker."""

from audit_engine.tasks.tracker import ProgressTracker


def test_initial_state():
    t = ProgressTracker()
    assert t.pct == 0.0
    assert t.active_branch == ""
    assert t.logs == []
    assert t.is_running is False
    assert t.summary is None
    assert t.cancel_requested is False


def test_reset_sets_running():
    t = ProgressTracker()
    t.reset()
    assert t.is_running is True
    assert t.pct == 0.0


def test_update_pct():
    t = ProgressTracker()
    t.reset()
    t.update_pct(50.0)
    assert t.pct == 50.0
    assert t.active_branch == ""


def test_update_pct_with_branch():
    t = ProgressTracker()
    t.reset()
    t.update_pct(75.0, active_branch="Branch A")
    assert t.pct == 75.0
    assert t.active_branch == "Branch A"


def test_log_appends_entry():
    t = ProgressTracker()
    t.log("INFO", "hello")
    assert len(t.logs) == 1
    entry = t.logs[0]
    assert entry["level"] == "INFO"
    assert entry["message"] == "hello"
    assert "timestamp" in entry


def test_log_thread_safety():
    t = ProgressTracker()
    for i in range(100):
        t.log("INFO", f"msg {i}")
    assert len(t.logs) == 100


def test_is_running_setter():
    t = ProgressTracker()
    t.is_running = True
    assert t.is_running is True
    t.is_running = False
    assert t.is_running is False


def test_summary_setter():
    t = ProgressTracker()
    s = {"title": "Done", "items": []}
    t.summary = s
    assert t.summary == s


def test_cancel_requested_setter():
    t = ProgressTracker()
    t.cancel_requested = True
    assert t.cancel_requested is True
    t.cancel_requested = False
    assert t.cancel_requested is False


def test_snapshot():
    t = ProgressTracker()
    t.reset()
    t.update_pct(42.0, "Branch X")
    t.log("OK", "all good")
    snap = t.snapshot()
    assert snap["pct"] == 42.0
    assert snap["active_branch"] == "Branch X"
    assert snap["is_running"] is True
    assert len(snap["logs"]) == 1


def test_snapshot_returns_copy():
    t = ProgressTracker()
    t.reset()
    snap = t.snapshot()
    snap["pct"] = 99.0
    assert t.pct == 0.0


def test_logs_returns_copy():
    t = ProgressTracker()
    t.log("INFO", "original")
    logs_copy = t.logs
    logs_copy.append({"level": "FAKE"})
    assert len(t.logs) == 1


def test_repr():
    t = ProgressTracker()
    assert "ProgressTracker" in repr(t)
    assert "pct" in repr(t)
