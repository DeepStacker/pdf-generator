"""Tests for database repository classes."""

import os

import pytest

from audit_engine.database import init_db
from audit_engine.database.repos import ConfigRepository, HistoryRepository
from audit_engine.domain.models import HistoryEntry


@pytest.fixture(autouse=True)
def _setup_db():
    init_db()
    yield


def test_config_repo_set_and_get():
    repo = ConfigRepository()
    repo.set("test_key", "test_value")
    assert repo.get("test_key") == "test_value"


def test_config_repo_get_default():
    repo = ConfigRepository()
    assert repo.get("nonexistent") is None
    assert repo.get("nonexistent", "fallback") == "fallback"


def test_config_repo_get_bool():
    repo = ConfigRepository()
    repo.set("flag", "True")
    assert repo.get_bool("flag") is True
    assert repo.get_bool("missing") is True
    assert repo.get_bool("missing", False) is False


def test_config_repo_get_int():
    repo = ConfigRepository()
    repo.set("num", "42")
    assert repo.get_int("num") == 42
    assert repo.get_int("nonexistent") == 0


def test_config_repo_overwrite():
    repo = ConfigRepository()
    repo.set("key", "first")
    repo.set("key", "second")
    assert repo.get("key") == "second"


def test_history_repo_add_and_list():
    repo = HistoryRepository()
    repo.add("test.xlsx", 5, "/tmp", "POA")
    entries = repo.list()
    assert len(entries) >= 1
    latest = entries[0]
    assert isinstance(latest, HistoryEntry)
    assert latest.excel_name == "test.xlsx"
    assert latest.pdf_count == 5


def test_history_repo_list_with_search():
    repo = HistoryRepository()
    repo.add("searchable.xlsx", 3, "/tmp", "TAF")
    results = repo.list(search="searchable")
    assert any(e.excel_name == "searchable.xlsx" for e in results)


def test_history_repo_stats():
    repo = HistoryRepository()
    sessions, pdfs = repo.stats()
    assert isinstance(sessions, int)
    assert isinstance(pdfs, int)


def test_history_repo_clear():
    repo = HistoryRepository()
    repo.add("clear_me.xlsx", 1, "/tmp", "POA")
    repo.clear()
    entries = repo.list()
    assert all(e.excel_name != "clear_me.xlsx" for e in entries)


def test_history_repo_last_run():
    repo = HistoryRepository()
    result = repo.last_run()
    assert result is not None


def test_history_repo_total_unique_excels():
    repo = HistoryRepository()
    count = repo.total_unique_excels()
    assert isinstance(count, int)


def test_config_repo_recent_files(tmp_path):
    repo = ConfigRepository()
    f1 = os.path.join(str(tmp_path), "f1.xlsx")
    f2 = os.path.join(str(tmp_path), "f2.xlsx")
    for p in (f1, f2):
        open(p, "w").close()
    repo.add_recent_file(f1)
    repo.add_recent_file(f2)
    recent = repo.get_recent_files()
    assert f1 in recent
    assert f2 in recent


def test_config_repo_clear_recent_files():
    repo = ConfigRepository()
    repo.clear_recent_files()
    assert repo.get_recent_files() == []
