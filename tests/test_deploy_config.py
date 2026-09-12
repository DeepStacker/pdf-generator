"""The deployment files a stranger has to get right on the first try.

None of this is exercised by running the app, so it drifts silently: a
variable renamed in compose and not in the template, a config that stops
being mounted, a script that points at a file nobody ships. Every one of
those shows up as a failed deploy on somebody else's machine.
"""

import os
import re
import stat
from pathlib import Path

import pytest

DEPLOY = Path(__file__).resolve().parent.parent / "deploy"


def read(name: str) -> str:
    return (DEPLOY / name).read_text()


@pytest.fixture(scope="module")
def template_keys() -> set[str]:
    return {
        line.split("=", 1)[0]
        for line in read(".env.production.example").splitlines()
        if line and not line.startswith("#") and "=" in line
    }


def referenced_vars(compose_name: str) -> set[str]:
    """Every ${NAME} a compose file interpolates, defaults and all."""
    return set(re.findall(r"\$\{([A-Z_][A-Z0-9_]*)", read(compose_name)))


@pytest.mark.parametrize("compose", ["compose.aws.yml", "compose.prod.yml"])
def test_every_variable_a_compose_file_reads_is_in_the_template(compose, template_keys):
    """A variable nobody knows to set is set to empty, quietly."""
    missing = sorted(referenced_vars(compose) - template_keys)
    assert not missing, f"{compose} reads variables the template never mentions: {missing}"


def test_the_aws_stack_publishes_a_port():
    """The tailnet stack deliberately publishes nothing. This one must.

    compose.prod.yml reaches the world through a Tailscale sidecar, so it has
    no ports at all. Copying that shape onto a normal host produces a stack
    that starts, reports healthy, and cannot be reached by anyone.
    """
    text = read("compose.aws.yml")
    assert "${HOST_PORT:-8080}:8080" in text
    # The prose may mention the tailnet stack; the services must not be it.
    assert "image: docker.io/tailscale" not in text, "the AWS stack should not need a tailnet"


def test_the_app_is_reachable_by_the_proxy_under_the_name_it_uses():
    """nginx proxies to `app`, which is the service name compose creates."""
    for conf in ("nginx/app.conf", "nginx/app-tls.conf"):
        assert "server app:8080;" in read(conf), f"{conf} points somewhere else"


def test_the_proxy_allows_an_upload_worth_making():
    """The point of this tool is a folder of PDFs; nginx defaults to 1MB."""
    for conf in ("nginx/app.conf", "nginx/app-tls.conf"):
        text = read(conf)
        assert re.search(r"client_max_body_size\s+\d+[GM];", text), f"{conf} keeps the 1MB default"
        # A merge takes longer than the 60s default, and the response only
        # starts once it is finished.
        assert re.search(r"proxy_read_timeout\s+\d{3,}s;", text), f"{conf} will time out mid-merge"


def test_the_proxy_passes_the_client_address_through():
    """Login throttling counts failures per client, so the hop must not eat it."""
    for conf in ("nginx/app.conf", "nginx/app-tls.conf"):
        assert re.search(
            r"proxy_set_header\s+X-Forwarded-For\s+\$proxy_add_x_forwarded_for;", read(conf)
        ), f"{conf} drops the client address"


def test_the_tls_config_reads_the_certificate_from_the_mounted_directory():
    text = read("nginx/app-tls.conf")
    assert "/etc/nginx/certs/fullchain.pem" in text
    assert "/etc/nginx/certs/privkey.pem" in text
    assert "${TLS_CERT_DIR:-./certs}:/etc/nginx/certs:ro" in read("compose.aws.yml")


def test_the_named_nginx_config_is_one_that_ships():
    """NGINX_CONF names a file inside deploy/nginx; a typo is a crash loop."""
    default = re.search(r"\$\{NGINX_CONF:-([^}]+)\}", read("compose.aws.yml"))
    assert default, "compose.aws.yml no longer picks a default nginx config"
    assert (DEPLOY / "nginx" / default.group(1)).is_file()

    named = re.search(r"^NGINX_CONF=(.+)$", read(".env.production.example"), re.M)
    assert named and (DEPLOY / "nginx" / named.group(1).strip()).is_file()


def test_the_bootstrap_script_is_executable_and_self_contained():
    script = DEPLOY / "bootstrap.sh"
    assert os.stat(script).st_mode & stat.S_IXUSR, "bootstrap.sh is not executable in git"

    text = script.read_text()
    assert "set -euo pipefail" in text
    # It must use the stack it claims to, and the template it copies from.
    assert "compose.aws.yml" in text
    assert ".env.production.example" in text
    # And it must never put the password on a command line, where `ps` reads it.
    assert "setpassword" in text
    assert not re.search(r"setpassword.*\$password", text)


def test_no_secret_ever_sits_in_the_template():
    """The example file is committed; it must hold nothing but blanks."""
    for line in read(".env.production.example").splitlines():
        if line.startswith(("GSS_AUTH_PASSWORD_HASH=", "GSS_SECRET_KEY=", "TS_AUTHKEY=")):
            assert line.split("=", 1)[1] == "", f"a value was committed: {line.split('=')[0]}"


def test_certificates_cannot_be_committed():
    """A private key in a public repository is not recoverable by a fix."""
    ignore = (DEPLOY.parent / ".gitignore").read_text()
    assert "deploy/certs/*" in ignore
    assert "deploy/.env.production" in ignore
