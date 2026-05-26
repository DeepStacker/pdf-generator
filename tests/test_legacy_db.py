"""Tests for uncovered functions in database/legacy.py."""

from audit_engine.database import (
    clear_history,
    get_analytics,
    get_last_run,
    get_recent_history,
    get_stats,
    get_total_unique_excels,
    init_db,
    log_generation,
    set_config,
)


def _setup():
    init_db()
    clear_history()
    set_config("test_key", "test_val")


def test_log_generation():
    _setup()
    log_generation("my_test.xlsx", 3, "/tmp/out", "POA")
    stats = get_stats()
    assert stats[0] >= 1
    assert stats[1] >= 3


def test_log_generation_with_full_path():
    _setup()
    log_generation("full.xlsx", 1, "/tmp", "TAF", full_path="/abs/full.xlsx")
    entries = get_recent_history()
    assert any(
        e[2] == "full.xlsx" and e[6] == "/abs/full.xlsx"
        for e in entries
    )


def test_get_stats_empty():
    clear_history()
    s, p = get_stats()
    assert s == 0
    assert p == 0


def test_get_stats_with_data():
    _setup()
    log_generation("a.xlsx", 5, "/tmp", "POA")
    log_generation("b.xlsx", 3, "/tmp", "TAF")
    s, p = get_stats()
    assert s >= 2
    assert p >= 8


def test_get_analytics():
    _setup()
    clear_history()
    log_generation("a.xlsx", 1, "/tmp", "POA")
    log_generation("b.xlsx", 2, "/tmp", "TAF")
    types, trend = get_analytics()
    assert "POA" in types
    assert "TAF" in types
    assert len(trend) >= 1


def test_get_recent_history_search():
    _setup()
    clear_history()
    log_generation("search_me.xlsx", 1, "/tmp", "POA")
    results = get_recent_history(search="search_me")
    assert len(results) >= 1
    assert any(r["excel_name"] == "search_me.xlsx" for r in results)


def test_get_recent_history_no_search():
    _setup()
    results = get_recent_history(limit=5)
    assert isinstance(results, list)


def test_clear_history():
    _setup()
    log_generation("clear_me.xlsx", 1, "/tmp", "POA")
    s_before = get_stats()[0]
    clear_history()
    s_after = get_stats()[0]
    assert s_after == 0 or s_after < s_before


def test_get_last_run_no_data():
    clear_history()
    result = get_last_run()
    assert result == "No activity yet"


def test_get_last_run_with_data():
    _setup()
    clear_history()
    log_generation("last.xlsx", 1, "/tmp", "POA")
    result = get_last_run()
    assert result != "No activity yet"


def test_get_total_unique_excels():
    _setup()
    clear_history()
    log_generation("unique.xlsx", 1, "/tmp", "POA")
    log_generation("unique.xlsx", 2, "/tmp", "POA")
    assert get_total_unique_excels() >= 1
