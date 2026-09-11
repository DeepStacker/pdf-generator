"""Shared test fixtures and configuration."""

import atexit
import os
import shutil
import sys
import tempfile

# Ensure src/ is on the path so we import the package under src/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# ---------------------------------------------------------------------------
# Point every user-level path at a throwaway directory, BEFORE audit_engine is
# imported anywhere.
#
# The suite used to run against the real application database -- the one the
# desktop app keeps in ~/Library/Application Support (or the Linux/Windows
# equivalent). Tests that exercise handle_run persist out_path, so running
# pytest silently repointed a developer's own output folder at a pytest
# tmp_path, which pytest then deleted a few runs later. Their next real run
# wrote reports into a directory that no longer existed.
#
# This has to happen at import time and cannot be a fixture. config.py
# resolves these once, at module level --
#
#     paths: Final[Paths] = Paths()
#
# -- and database/legacy.py opens a module-level singleton connection to
# paths.db on first use. By the time any fixture runs, both are already bound
# to the real locations. Setting the environment here, before the first
# `import audit_engine`, is what makes the redirection stick. pytest imports
# conftest before collecting test modules, so this is early enough.
# ---------------------------------------------------------------------------
_TEST_STATE_DIR = tempfile.mkdtemp(prefix="audit_engine_tests_")

os.environ["AUDIT_ENGINE_DB_PATH"] = os.path.join(_TEST_STATE_DIR, "test.db")
os.environ["AUDIT_ENGINE_LOG_PATH"] = os.path.join(_TEST_STATE_DIR, "test.log")
os.environ.setdefault("REPORT_STORAGE_DIR", os.path.join(_TEST_STATE_DIR, "reports"))

atexit.register(lambda: shutil.rmtree(_TEST_STATE_DIR, ignore_errors=True))


# Imported after the environment is set on purpose: pytest pulls in plugins
# that import the package under test, and anything that touches audit_engine
# before the lines above binds paths.db to the real database.
import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _unbound_user():
    """Leave every test with no user bound to this thread.

    Job state and settings are keyed on a thread-local current user, so a
    test that binds one and then fails -- or simply forgets -- leaves the
    binding in place for everything that runs after it in the same thread.
    That is not hypothetical: binding a user in the multi-user tests made six
    desktop tests fail purely by running after them, because the config keys
    they read were suddenly prefixed.
    """
    from audit_engine.app import _ipc_mode
    from audit_engine.tasks import session

    session.unbind()
    _ipc_mode.enabled = False
    yield
    session.unbind()
    # Constructing a WebViewBridge switches the process into IPC mode, where
    # the HTTP password gate does not apply. Left set, it would make a later
    # test think the gate had been disabled.
    _ipc_mode.enabled = False

    # Importing the web server calls apply_patches(), which rewires
    # desktop-only handlers for the whole process. Left in place it makes the
    # order of test files matter: anything importing the server before the
    # desktop tests made them fail with "Not available in web mode".
    try:
        from audit_engine_web.patches import revert_patches
    except Exception:
        return
    revert_patches()


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





def test_the_suite_is_not_using_the_real_application_database():
    """A guard, deliberately in conftest so it cannot be deleted with a file.

    If this fails, running the suite is writing to whatever database the
    desktop app on this machine uses, and a developer's own settings are
    being overwritten by tests.
    """
    from audit_engine.utils.config import paths

    resolved = os.path.realpath(paths.db)
    assert resolved.startswith(os.path.realpath(_TEST_STATE_DIR)), (
        f"tests are using {resolved}, not the throwaway directory. Something "
        f"imported audit_engine before conftest set the environment."
    )

    for marker in ("Application Support", ".local/share", "AppData"):
        assert marker not in resolved, f"tests are writing to a real user directory: {resolved}"
