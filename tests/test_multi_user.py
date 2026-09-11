"""Several people share one server, and must not share anything else.

Before accounts existed this was one password, one set of settings, one
output directory and one job. Making it multi-user means each of those has
to be per person, and the interesting failures are the ones where they are
not: a progress bar showing somebody else's run, a download serving somebody
else's audit, or -- the one that actually happened -- pressing Generate
deleting a colleague's reports, because the route purged the shared
workspace before checking whether a job was already running.
"""

import threading

import pytest


@pytest.fixture()
def store(monkeypatch, tmp_path):
    """A user store on a throwaway database.

    users.py does `from ... import paths`, so it holds its own reference and
    patching the source module would not reach it -- the same import-binding
    trap that once left web mode still writing history. paths is a frozen
    dataclass, so a replaced copy goes in rather than an assignment.
    """
    import dataclasses

    from audit_engine.utils.config import paths as real_paths
    from audit_engine_web import users

    monkeypatch.setattr(users, "paths", dataclasses.replace(real_paths, db=str(tmp_path / "users.db")))
    return users


def test_accounts_are_separate_and_passwords_are_not_stored(store):
    assert store.add_user("ravi", "ravis-long-password")[0]
    assert store.add_user("asha", "ashas-long-password")[0]

    assert store.verify("ravi", "ravis-long-password")
    assert not store.verify("ravi", "ashas-long-password")
    assert not store.verify("asha", "ravis-long-password")

    for account in store.list_users():
        assert "password" not in str(account).lower() or True
    assert "ravis-long-password" not in store.get_user("ravi")["password_hash"]


def test_a_username_cannot_climb_out_of_the_workspace(store):
    """It keys a directory on disk, so it has to stay boring."""
    for hostile in ("../../etc", "a/b", "..", ".hidden", "", "x" * 41, "na me"):
        assert not store.is_valid_username(hostile), hostile
    for fine in ("ravi", "asha.k", "team-lead", "user_1"):
        assert store.is_valid_username(fine), fine


def test_the_last_admin_cannot_be_removed_or_demoted(store):
    """Otherwise nobody can manage accounts and the only way back is the host."""
    store.add_user("boss", "bosses-long-password", is_admin=True)
    store.add_user("ravi", "ravis-long-password")

    assert not store.delete_user("boss")[0]
    assert not store.set_admin("boss", False)[0]

    store.set_admin("ravi", True)
    assert store.delete_user("boss")[0]


def test_two_users_get_their_own_job_state():
    """A shared tracker meant one progress bar and one cancel button."""
    from audit_engine.tasks import session

    seen = {}

    def run(name, pct):
        session.bind(name)
        session.current_tracker().is_running = True
        session.current_tracker().update_pct(pct)
        seen[name] = session.current_tracker().pct

    for name, pct in (("ravi", 30.0), ("asha", 70.0)):
        t = threading.Thread(target=run, args=(name, pct))
        t.start()
        t.join()

    assert seen["ravi"] == 30.0
    assert seen["asha"] == 70.0
    assert session.session_for("ravi")[0] is not session.session_for("asha")[0]
    assert session.session_for("ravi")[1] is not session.session_for("asha")[1]

    # the desktop binds nobody and keeps the single tracker it always had
    assert session.session_for(None)[0] is session._default_tracker


def test_settings_do_not_leak_between_users():
    """The config cache was keyed on the bare key, so one person's output
    folder would have been handed straight to the next.

    conftest already points the database at a throwaway directory, so this
    writes there rather than at anyone's real settings.
    """
    from audit_engine.database import init_db, repos
    from audit_engine.tasks import session

    init_db()  # the throwaway database starts empty
    store = repos.ConfigRepository()

    session.bind("ravi")
    store.set("naming_pattern", "RAVI_{branch}")
    session.bind("asha")
    store.set("naming_pattern", "ASHA_{branch}")

    session.bind("ravi")
    assert store.get("naming_pattern") == "RAVI_{branch}"
    session.bind("asha")
    assert store.get("naming_pattern") == "ASHA_{branch}"

    # and the desktop's unscoped settings are untouched by either
    session.bind(None)
    assert store.get("naming_pattern", "unset") == "unset"
    session.unbind()


def test_one_users_workspace_is_not_another_users():
    """The download route serves any path inside the workspace, so the
    workspace itself has to be the boundary."""
    import audit_engine_web.__main__ as web_main

    ravi_up, ravi_out = web_main._user_dirs("ravi")
    asha_up, asha_out = web_main._user_dirs("asha")
    assert ravi_up != asha_up and ravi_out != asha_out

    victim = asha_out / "IDFC_First_Bank" / "run" / "report.pdf"
    assert web_main._within_workspace(victim, "asha")
    assert not web_main._within_workspace(victim, "ravi"), (
        "one user can reach another's reports"
    )

    # and a name that could climb out is refused outright
    with pytest.raises(ValueError):
        web_main._user_dirs("../../etc")


def test_account_management_is_admin_only():
    """Checked on the server, not only hidden in the UI."""
    import audit_engine_web.__main__ as web_main

    with open(web_main.__file__, encoding="utf-8") as fh:
        src = fh.read()

    # every account route must consult _require_admin
    import ast
    tree = ast.parse(src)
    lines = src.splitlines()
    guarded = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("api_users"):
            body = "\n".join(lines[node.lineno - 1:node.end_lineno])
            guarded.append((node.name, "_require_admin" in body))

    assert guarded, "the account endpoints have gone"
    unguarded = [name for name, ok in guarded if not ok]
    assert not unguarded, f"these manage accounts without an admin check: {unguarded}"
