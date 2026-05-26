"""Auto-update logic: check GitHub releases, download, and install binaries."""

import contextlib
import hashlib
import json
import os
import shutil as _shutil
import ssl
import stat
import subprocess
import sys
import tempfile as _tempfile
import threading
import urllib.error as _urlerror
import urllib.request as _urllib
import zipfile
from collections.abc import Callable
from http.client import HTTPResponse

from audit_engine._version import VERSION
from audit_engine.utils.config import update
from audit_engine.utils.platform import file_logger


class UpdateState:
    def __init__(self) -> None:
        self.update_ready: bool = False
        self.latest_version: str = ""
        self.binary_url: str = ""
        self.expected_sha256: str = ""
        self.dest_zip_path: str = ""
        self.progress_pct: float = 0.0
        self.is_downloading: bool = False
        self.success: bool = False
        self.error: str = ""
        self.staged_bat: str | None = None


update_state: UpdateState = UpdateState()


def _make_ssl_context() -> ssl.SSLContext:
    try:
        import certifi
        cafile = certifi.where()
        if os.path.exists(cafile):
            return ssl.create_default_context(cafile=cafile)
    except Exception as exc:
        file_logger.warning("SSL context init: %s", exc)
    return ssl.create_default_context()


def _urlopen_with_fallback(req: _urllib.Request, timeout: int = 10) -> HTTPResponse:
    ctx = _make_ssl_context()
    try:
        return _urllib.urlopen(req, context=ctx, timeout=timeout)
    except _urlerror.URLError as e:
        if "CERTIFICATE_VERIFY_FAILED" in str(e):
            file_logger.warning("SSL cert verification failed, attempting without verification")
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            return _urllib.urlopen(req, context=ctx, timeout=timeout)
        raise


def _get_platform_suffix() -> str:
    if sys.platform == "darwin":
        return "macos"
    elif sys.platform == "win32":
        return "windows"
    return "linux"


def _check_latest_release() -> tuple[str, str, str, str, str]:
    req = _urllib.Request(update.github_api, headers={"User-Agent": f"AuditEngine/{VERSION}"})
    with _urlopen_with_fallback(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
    tag: str = data["tag_name"]
    source_url: str = data["zipball_url"]
    body: str = data.get("body", "")

    suffix = _get_platform_suffix()
    binary_url: str = ""
    expected_sha256: str = ""

    if suffix == "macos":
        keywords = ["macos", "mac-os", "darwin", "osx", "mac"]
    elif suffix == "windows":
        keywords = ["windows", "win32", "win64", "win"]
    else:
        keywords = ["linux", "ubuntu", "debian"]

    for asset in data.get("assets", []):
        asset_name: str = asset["name"].lower()
        is_platform_match = any(kw in asset_name for kw in keywords)
        is_package_ext = asset_name.endswith(".zip") or asset_name.endswith(".tar.gz") or (suffix == "windows" and asset_name.endswith(".exe"))

        if is_platform_match and is_package_ext:
            binary_url = asset["browser_download_url"]
            break

    if not binary_url and data.get("assets"):
        binary_url = data["assets"][0]["browser_download_url"]

    # Look for a matching SHA256 checksum asset
    if binary_url:
        checksum_name = os.path.basename(binary_url) + ".sha256"
        for asset in data.get("assets", []):
            if asset["name"] == checksum_name:
                try:
                    req_hash = _urllib.Request(asset["browser_download_url"], headers={"User-Agent": f"AuditEngine/{VERSION}"})
                    with _urlopen_with_fallback(req_hash, timeout=10) as resp_hash:
                        expected_sha256 = resp_hash.read().decode().strip().split()[0]
                except Exception as exc:
                    file_logger.warning("Could not fetch checksum asset: %s", exc)
                break

    return tag, source_url, body, binary_url, expected_sha256


def _parse_version(tag: str) -> tuple[int, ...]:
    parts = tag.lstrip("vV").split(".")
    result: list[int] = []
    for p in parts:
        try:
            result.append(int(p))
        except ValueError:
            return (0,)
    return tuple(result)


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _download_update(url: str, dest_path: str, progress_callback: Callable[[float], None] | None = None) -> str:
    req = _urllib.Request(url, headers={"User-Agent": f"AuditEngine/{VERSION}"})
    with _urlopen_with_fallback(req, timeout=60) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        with open(dest_path, "wb") as f:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback and total:
                    progress_callback(downloaded / total * 100)
    return dest_path


def _install_binary_update(zip_path: str, install_dir: str, log_callback: Callable[[str], None] = print) -> str | None:
    import shutil
    extract_to = _tempfile.mkdtemp(prefix="audit_bin_")
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            member_path = os.path.normpath(os.path.join(extract_to, member.filename))
            if not member_path.startswith(os.path.normpath(extract_to)):
                raise RuntimeError(f"Path traversal detected in update ZIP: {member.filename}")
        zf.extractall(extract_to)
    for root, dirs, files in os.walk(extract_to):
        for f in files:
            fp = os.path.join(root, f)
            st = os.stat(fp)
            os.chmod(fp, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    src = None
    for root, dirs, files in os.walk(extract_to):
        for f in files:
            fp = os.path.join(root, f)
            if os.access(fp, os.X_OK):
                src = fp
                break
        if src:
            break
    if not src:
        raise RuntimeError("No executable found in update ZIP")
    old_exe = sys.executable
    log_callback(f"Replacing {old_exe} with {src}")
    if sys.platform == "win32":
        backup = old_exe + ".bak"
        if os.path.exists(backup):
            with contextlib.suppress(OSError):
                os.remove(backup)
        os.rename(old_exe, backup)
        shutil.copy2(src, old_exe)
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
        subprocess.Popen(
            [old_exe],
            close_fds=True,
            startupinfo=startup,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
        log_callback("Update staged in-place. Launching new binary and cleanly exiting.")
        return "IN_PLACE_UPDATE"

    backup = old_exe + ".bak"
    if os.path.exists(old_exe):
        os.rename(old_exe, backup)
    os.makedirs(os.path.dirname(old_exe), exist_ok=True)
    shutil.copy2(src, old_exe)
    os.chmod(old_exe, 0o755)
    if sys.platform == "darwin":
        subprocess.run(["xattr", "-dr", "com.apple.quarantine", old_exe], check=False)
    if os.path.exists(backup):
        os.remove(backup)
    shutil.rmtree(extract_to, ignore_errors=True)
    log_callback(f"Binary updated at {old_exe}")
    return None


def _get_install_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _cleanup_stale_mei() -> None:
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return
    try:
        temp_dir = _tempfile.gettempdir()
        current_mei = getattr(sys, '_MEIPASS', '')
        current_mei_name = os.path.basename(current_mei).lower() if current_mei else ""
        for entry in os.listdir(temp_dir):
            if not entry.startswith('_MEI'):
                continue
            if entry.lower() == current_mei_name:
                continue
            mei_path = os.path.join(temp_dir, entry)
            if not os.path.isdir(mei_path):
                continue
            with contextlib.suppress(PermissionError, OSError):
                _shutil.rmtree(mei_path)
    except Exception:
        pass


def _restart_app() -> None:
    if sys.platform == "win32":
        subprocess.Popen([sys.executable] + (sys.argv if not getattr(sys, "frozen", False) else []))
        sys.exit(0)
    if getattr(sys, "frozen", False):
        os.execl(sys.executable, sys.executable)
    else:
        os.execl(sys.executable, sys.executable, *sys.argv)


def check_latest_release() -> dict:
    try:
        tag, source_url, body, binary_url, expected_sha256 = _check_latest_release()
        current_v = _parse_version(VERSION)
        latest_v = _parse_version(tag)
        if latest_v > current_v:
            if binary_url:
                update_state.update_ready = True
                update_state.latest_version = tag
                update_state.binary_url = binary_url
                update_state.expected_sha256 = expected_sha256
                return {
                    "update_ready": True,
                    "current": VERSION,
                    "latest": tag,
                    "body": body
                }
            else:
                file_logger.info(f"Update tag {tag} exists, but binary for OS is missing/building. Deferring.")
    except Exception as e:
        file_logger.warning(f"Background updates repo search query failed: {e}")
    return {"update_ready": False, "current": VERSION}


def download_update_worker(expected_sha256: str = "") -> None:
    dest_dir = _tempfile.mkdtemp(prefix="audit_update_")
    try:
        update_state.is_downloading = True
        update_state.progress_pct = 0.0
        update_state.success = False
        update_state.error = ""

        dest_zip = os.path.join(dest_dir, "update.zip")
        update_state.dest_zip_path = dest_zip

        def progress_cb(pct: float) -> None:
            update_state.progress_pct = pct

        _download_update(update_state.binary_url, dest_zip, progress_cb)

        if expected_sha256:
            actual = _sha256_file(dest_zip)
            if actual != expected_sha256:
                raise RuntimeError(f"SHA256 mismatch: expected {expected_sha256}, got {actual}")

        install_dir = _get_install_dir()
        bat = _install_binary_update(dest_zip, install_dir, log_callback=file_logger.info)
        if bat:
            update_state.staged_bat = bat

        update_state.success = True
        update_state.progress_pct = 100.0
    except Exception as e:
        update_state.error = str(e)
        update_state.success = False
    finally:
        update_state.is_downloading = False
        if not update_state.success and os.path.isdir(dest_dir):
            _shutil.rmtree(dest_dir, ignore_errors=True)


if getattr(sys, "frozen", False):
    threading.Thread(target=_cleanup_stale_mei, daemon=True).start()
