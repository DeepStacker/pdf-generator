"""The browser server must not answer to strangers.

It is reachable from the public internet and every route behind it acts on
customers' audit workbooks. It authenticated nobody until this existed.

The test that matters most here is the one asserting the body is empty.
The first version of the gate was a bottle before_request hook that
*returned* a 401. bottle collects hook return values and discards them --
trigger_hook builds a list and throws it away -- so the handler ran anyway:
an unauthenticated GET / answered "401" and served the entire application,
and /api/history answered "401" with the history in the body. Checking the
status code alone would have passed. Only the body gave it away.
"""

import json

import pytest

from audit_engine_web import auth


@pytest.fixture()
def configured(monkeypatch):
    monkeypatch.setenv(auth.PASSWORD_ENV, auth.hash_password("a-long-enough-password"))
    monkeypatch.setenv(auth.SECRET_ENV, "test-secret-key")


def test_a_hash_never_contains_the_password():
    encoded = auth.hash_password("hunter2-hunter2")
    assert "hunter2" not in encoded
    assert encoded.startswith("pbkdf2_sha256$")


def test_only_the_right_password_verifies():
    encoded = auth.hash_password("a-long-enough-password")
    assert auth.verify_password("a-long-enough-password", encoded)
    assert not auth.verify_password("a-long-enough-passwore", encoded)
    assert not auth.verify_password("", encoded)


@pytest.mark.parametrize("junk", ["", "nonsense", "a$b$c$d", "pbkdf2_sha256$x$y$z"])
def test_a_malformed_hash_rejects_rather_than_raises(junk):
    """A broken config value must not take the process down, or worse, pass."""
    assert auth.verify_password("anything", junk) is False


def test_a_session_cannot_be_forged_or_edited(configured):
    token = auth.issue_session()
    assert auth.session_is_valid(token)

    issued, signature = token.rsplit(".", 1)
    assert not auth.session_is_valid(f"{issued}.{'0' * len(signature)}")
    assert not auth.session_is_valid(f"{int(issued) - 1}.{signature}")  # re-dated
    assert not auth.session_is_valid("nonsense")
    assert not auth.session_is_valid(None)


def test_a_session_expires(configured, monkeypatch):
    token = auth.issue_session()
    real_time = auth.time.time
    monkeypatch.setattr(auth.time, "time", lambda: real_time() + auth.SESSION_MAX_AGE + 60)
    assert not auth.session_is_valid(token), "an expired session still opened the door"


def test_a_session_signed_with_another_key_is_refused(configured, monkeypatch):
    token = auth.issue_session()
    monkeypatch.setenv(auth.SECRET_ENV, "a-different-key")
    assert not auth.session_is_valid(token)


def test_repeated_failures_are_throttled():
    client = "203.0.113.9"
    auth.clear_failures(client)
    assert not auth.is_throttled(client)
    for _ in range(20):
        auth.note_failure(client)
    assert auth.is_throttled(client), "an internet-facing password form with no rate limit"
    auth.clear_failures(client)
    assert not auth.is_throttled(client)


def test_the_gate_blocks_rather_than_merely_labelling(monkeypatch):
    """It must RAISE. Returning a response from a bottle hook does nothing.

    Reproduces the real failure: if the hook returns instead of raising, the
    route still runs and its body is served alongside the 401.
    """
    import audit_engine_web.__main__ as web_main
    from audit_engine.lib.bottle import HTTPResponse

    monkeypatch.setenv(auth.PASSWORD_ENV, auth.hash_password("a-long-enough-password"))
    monkeypatch.setenv(auth.SECRET_ENV, "test-secret-key")

    class _Req:
        path = "/api/history"

        @staticmethod
        def get_cookie(_name):
            return None

    monkeypatch.setattr(web_main, "request", _Req)

    with pytest.raises(HTTPResponse) as caught:
        web_main._require_login()

    refused = caught.value
    assert refused.status_code == 401
    assert json.loads(refused.body)["success"] is False


def test_the_login_page_and_the_icons_stay_reachable():
    """A visitor has to be able to load the form they are being sent to."""
    import audit_engine_web.__main__ as web_main

    for path in ("/login", "/logout", "/favicon.ico", "/manifest.webmanifest", "/sw.js", "/icon-192.png"):
        assert web_main._is_open_path(path), f"{path} is gated, so the login page cannot render"

    for path in ("/", "/api/history", "/api/run", "/assets/index-abc.js"):
        assert not web_main._is_open_path(path), f"{path} is reachable without signing in"
