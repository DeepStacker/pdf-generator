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
import tarfile
import tempfile as _tempfile
import threading
import time
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
        self._lock = threading.Lock()
        self.update_ready: bool = False
        self.latest_version: str = ""
        self.binary_url: str = ""
        self.dest_zip_path: str = ""
        self.staged_bat: str | None = None
        self._expected_sha256: str = ""
        self._progress_pct: float = 0.0
        self._is_downloading: bool = False
        self._success: bool = False
        self._error: str = ""
        self._preflight_pass: bool = False
        self._preflight_result: dict = {}
        self._release_body: str = ""
        self._last_check_time: float = 0.0
        self._current_check_result: dict = {}

    @property
    def expected_sha256(self) -> str:
        with self._lock:
            return self._expected_sha256

    @expected_sha256.setter
    def expected_sha256(self, value: str) -> None:
        with self._lock:
            self._expected_sha256 = value

    @property
    def progress_pct(self) -> float:
        with self._lock:
            return self._progress_pct

    @progress_pct.setter
    def progress_pct(self, value: float) -> None:
        with self._lock:
            self._progress_pct = value

    @property
    def is_downloading(self) -> bool:
        with self._lock:
            return self._is_downloading

    @is_downloading.setter
    def is_downloading(self, value: bool) -> None:
        with self._lock:
            self._is_downloading = value

    @property
    def success(self) -> bool:
        with self._lock:
            return self._success

    @success.setter
    def success(self, value: bool) -> None:
        with self._lock:
            self._success = value

    @property
    def error(self) -> str:
        with self._lock:
            return self._error

    @error.setter
    def error(self, value: str) -> None:
        with self._lock:
            self._error = value

    @property
    def preflight_pass(self) -> bool:
        with self._lock:
            return self._preflight_pass

    @preflight_pass.setter
    def preflight_pass(self, value: bool) -> None:
        with self._lock:
            self._preflight_pass = value

    @property
    def preflight_result(self) -> dict:
        with self._lock:
            return self._preflight_result

    @preflight_result.setter
    def preflight_result(self, value: dict) -> None:
        with self._lock:
            self._preflight_result = value

    @property
    def release_body(self) -> str:
        with self._lock:
            return self._release_body

    @release_body.setter
    def release_body(self, value: str) -> None:
        with self._lock:
            self._release_body = value

    @property
    def last_check_time(self) -> float:
        with self._lock:
            return self._last_check_time

    @last_check_time.setter
    def last_check_time(self, value: float) -> None:
        with self._lock:
            self._last_check_time = value

    @property
    def current_check_result(self) -> dict:
        with self._lock:
            return self._current_check_result

    @current_check_result.setter
    def current_check_result(self, value: dict) -> None:
        with self._lock:
            self._current_check_result = value


update_state: UpdateState = UpdateState()


def _make_ssl_context() -> ssl.SSLContext:
    """Create an SSL context suitable for corporate environments.

    Priority order:
    1. System certificate store (includes corporate CA certs from Sophos/MITM proxies)
    2. Bundled certifi CA bundle (fallback for environments without system certs)
    3. Default Python SSL context (last resort)
    """
    # Try system cert store first — corporate environments inject their CA here
    try:
        ctx = ssl.create_default_context()
        # On Windows, ssl.create_default_context() automatically loads the Windows cert store.
        # On macOS, it loads the Keychain. On Linux, it uses /etc/ssl/certs.
        return ctx
    except Exception as exc:
        file_logger.warning("System cert store unavailable: %s", exc)

    # Fallback to bundled certifi
    try:
        import certifi
        cafile = certifi.where()
        if os.path.exists(cafile):
            return ssl.create_default_context(cafile=cafile)
    except Exception as exc:
        file_logger.warning("Certifi fallback failed: %s", exc)

    return ssl.create_default_context()


def _urlopen_with_fallback(req: _urllib.Request, timeout: int = 15) -> HTTPResponse:
    """Open a URL with SSL fallback and proxy awareness.

    Corporate environments may:
    - Use MITM SSL inspection (Sophos, Zscaler) — handled by system cert store
    - Route through HTTP/HTTPS proxies — handled by ProxyHandler
    - Have slow networks — handled by increased timeouts
    """
    ctx = _make_ssl_context()

    # Build an opener that respects system proxy settings (HTTP_PROXY, HTTPS_PROXY, etc.)
    proxy_handler = _urllib.ProxyHandler()  # Auto-detects system proxy
    https_handler = _urllib.HTTPSHandler(context=ctx)
    opener = _urllib.build_opener(proxy_handler, https_handler)

    try:
        return opener.open(req, timeout=timeout)
    except _urlerror.URLError as e:
        if "CERTIFICATE_VERIFY_FAILED" in str(e):
            file_logger.warning("SSL cert verification failed — retrying without verification (corporate MITM likely)")
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            https_handler = _urllib.HTTPSHandler(context=ctx)
            opener = _urllib.build_opener(proxy_handler, https_handler)
            return opener.open(req, timeout=timeout)
        raise


def _get_platform_suffix() -> str:
    if sys.platform == "darwin":
        return "macos"
    elif sys.platform == "win32":
        return "windows"
    return "linux"


def _extract_archive(archive_path: str, extract_to: str) -> None:
    if archive_path.endswith((".tar.gz", ".tgz")):
        with tarfile.open(archive_path, "r:gz") as tar:
            for member in tar.getmembers():
                member_path = os.path.normpath(os.path.join(extract_to, member.name))
                if not member_path.startswith(os.path.normpath(extract_to)):
                    raise RuntimeError(f"Path traversal detected in update archive: {member.name}")
            tar.extractall(extract_to, filter="data")
    else:
        with zipfile.ZipFile(archive_path, "r") as zf:
            for zip_member in zf.infolist():
                member_path = os.path.normpath(os.path.join(extract_to, zip_member.filename))
                if not member_path.startswith(os.path.normpath(extract_to)):
                    raise RuntimeError(f"Path traversal detected in update archive: {zip_member.filename}")

                # Create parent directory
                os.makedirs(os.path.dirname(member_path), exist_ok=True)

                # Check for symlink attribute (0xA000 in high-order word of external_attr)
                is_symlink = (zip_member.external_attr >> 16) & 0o170000 == 0o120000
                if is_symlink:
                    link_target = zf.read(zip_member).decode("utf-8").strip()
                    if os.path.lexists(member_path):
                        with contextlib.suppress(OSError):
                            os.remove(member_path)
                    os.symlink(link_target, member_path)
                elif zip_member.is_dir():
                    os.makedirs(member_path, exist_ok=True)
                else:
                    with zf.open(zip_member) as source, open(member_path, "wb") as target:
                        _shutil.copyfileobj(source, target)
                    # Restore file permissions
                    attr = zip_member.external_attr >> 16
                    if attr:
                        os.chmod(member_path, attr)


def _is_macos_app_bundle() -> bool:
    if sys.platform != "darwin" or not getattr(sys, "frozen", False):
        return False
    return ".app/Contents/MacOS/" in (os.path.normpath(sys.executable or ""))


def _macos_codesign(path: str) -> None:
    if sys.platform != "darwin":
        return
    try:
        subprocess.run(["codesign", "--force", "--deep", "--sign", "-", path], capture_output=True, timeout=30, check=False)
    except Exception as exc:
        file_logger.warning("macOS ad-hoc code signing failed (non-fatal): %s", exc)


def _get_current_app_bundle_path() -> str | None:
    if not _is_macos_app_bundle():
        return None
    parts = os.path.normpath(sys.executable or "").split(os.sep)
    for i, part in enumerate(parts):
        if part.endswith(".app"):
            return os.sep.join(parts[: i + 1])
    return None


_MIN_DISK_MB = 200


def _preflight_check(install_dir: str = "", binary_url: str = "") -> dict:
    result: dict = {"pass": True, "checks": {}}

    frozen = getattr(sys, "frozen", False)
    result["checks"]["frozen"] = frozen
    if not frozen:
        result["pass"] = False

    exe = sys.executable or ""
    exe_ok = bool(exe) and os.path.isfile(exe)
    result["checks"]["current_executable"] = exe_ok
    if not exe_ok:
        result["pass"] = False

    if not install_dir:
        install_dir = _get_install_dir()
    dir_exists = os.path.isdir(install_dir) if install_dir else False
    dir_writable = os.access(install_dir, os.W_OK) if dir_exists else False
    result["checks"]["install_dir"] = install_dir
    result["checks"]["install_dir_exists"] = dir_exists
    result["checks"]["install_dir_writable"] = dir_writable
    if not dir_exists or not dir_writable:
        result["pass"] = False

    for label, path in [("install", install_dir), ("temp", _tempfile.gettempdir())]:
        try:
            usage = _shutil.disk_usage(path)
            free_mb = usage.free // (1024 * 1024)
            result["checks"][f"{label}_free_mb"] = free_mb
            if free_mb < _MIN_DISK_MB:
                result["pass"] = False
        except Exception:
            result["checks"][f"{label}_free_mb"] = -1
            result["pass"] = False

    if binary_url:
        suffix = _get_platform_suffix()
        url_lower = binary_url.lower()
        _keywords = {
            "macos": ["macos", "mac-os", "darwin", "osx", "mac"],
            "windows": ["windows", "win32", "win64", "win"],
            "linux": ["linux", "ubuntu", "debian"],
        }
        expected = _keywords.get(suffix, [])
        platform_ok = any(kw in url_lower for kw in expected) if expected else True
        result["checks"]["platform_match"] = platform_ok
        if not platform_ok:
            result["pass"] = False

        try:
            req = _urllib.Request(binary_url, method="HEAD", headers={"User-Agent": f"AuditEngine/{VERSION}"})
            with _urlopen_with_fallback(req, timeout=5) as resp:
                result["checks"]["network_reachable"] = True
                result["checks"]["remote_size_mb"] = (int(resp.headers.get("Content-Length", 0)) or 0) // (1024 * 1024)
        except Exception:
            result["checks"]["network_reachable"] = False
            result["pass"] = False

    result["checks"]["min_disk_mb"] = _MIN_DISK_MB
    return result


_CHECK_INTERVAL = 3600
_BACKGROUND_DELAY = 15


def _background_check_worker() -> None:
    threading.Event().wait(_BACKGROUND_DELAY)
    while True:
        try:
            file_logger.info("Background update check starting...")
            result = check_latest_release()
            file_logger.info("Background update check complete (ready=%s, preflight=%s)",
                            result.get("update_ready"),
                            update_state.preflight_pass)
        except Exception as exc:
            file_logger.warning("Background update check failed: %s", exc)
        threading.Event().wait(_CHECK_INTERVAL)


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
                        raw_data = resp_hash.read()
                        # Try decoding with multiple encodings (including UTF-16 with BOM for Windows certutil logs)
                        for encoding in ("utf-8", "utf-16", "ascii", "latin-1"):
                            try:
                                text = raw_data.decode(encoding)
                                import re
                                match = re.search(r"\b([a-fA-F0-9]{64})\b", text)
                                if match:
                                    expected_sha256 = match.group(1).lower()
                                    break
                            except Exception:
                                continue
                except Exception as exc:
                    file_logger.warning("Could not fetch checksum asset: %s", exc)
                break

    return tag, source_url, body, binary_url, expected_sha256


def _parse_version(tag: str) -> tuple[int, ...]:
    import re
    parts = tag.lstrip("vV").split(".")
    result: list[int] = []
    for p in parts:
        match = re.match(r"^(\d+)", p)
        if match:
            result.append(int(match.group(1)))
        else:
            result.append(0)
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


def _install_binary_update(archive_path: str, install_dir: str, log_callback: Callable[[str], None] = print) -> str | None:
    extract_to = _tempfile.mkdtemp(prefix="audit_bin_")
    try:
        _extract_archive(archive_path, extract_to)

        for root, dirs, files in os.walk(extract_to):
            for f in files:
                fp = os.path.join(root, f)
                st = os.stat(fp)
                os.chmod(fp, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        # macOS .app bundle replacement
        if _is_macos_app_bundle():
            app_bundles = []
            for root, dirs, files in os.walk(extract_to):
                for d in dirs:
                    if d.endswith(".app"):
                        app_bundles.append(os.path.join(root, d))
                if app_bundles:
                    break
            if app_bundles:
                current_app = _get_current_app_bundle_path()
                if current_app and os.path.isdir(current_app):
                    backup = current_app + ".bak"
                    if os.path.exists(backup):
                        _shutil.rmtree(backup, ignore_errors=True)
                    os.rename(current_app, backup)
                    _shutil.copytree(app_bundles[0], current_app, symlinks=True)
                    _macos_codesign(current_app)
                    _shutil.rmtree(backup, ignore_errors=True)
                    log_callback(f"App bundle updated at {current_app}")
                    return None

        src = None
        for root, dirs, files in os.walk(extract_to):
            for f in files:
                fp = os.path.join(root, f)
                if sys.platform == "win32":
                    if f.lower().endswith(".exe"):
                        src = fp
                        break
                elif os.access(fp, os.X_OK):
                    src = fp
                    break
            if src:
                break
        if not src:
            raise RuntimeError("No executable found in update archive")

        old_exe = sys.executable
        log_callback(f"Replacing {old_exe} with {src}")

        if sys.platform == "win32":
            backup = old_exe + ".bak"
            if os.path.exists(backup):
                with contextlib.suppress(OSError):
                    os.remove(backup)
            os.rename(old_exe, backup)
            _shutil.copy2(src, old_exe)
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
        _shutil.copy2(src, old_exe)
        os.chmod(old_exe, 0o755)

        if sys.platform == "darwin":
            subprocess.run(["xattr", "-dr", "com.apple.quarantine", old_exe], check=False)
            _macos_codesign(old_exe)

        if os.path.exists(backup):
            os.remove(backup)

        log_callback(f"Binary updated at {old_exe}")
        return None
    finally:
        _shutil.rmtree(extract_to, ignore_errors=True)


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


def check_latest_release(force: bool = False) -> dict:
    cached = update_state.current_check_result
    last = update_state.last_check_time
    if not force and cached and last > 0 and (time.monotonic() - last) < _CHECK_INTERVAL:
        return cached

    result: dict = {"update_ready": False, "current": VERSION}
    try:
        tag, source_url, body, binary_url, expected_sha256 = _check_latest_release()
        current_v = _parse_version(VERSION)
        latest_v = _parse_version(tag)
        frozen = getattr(sys, "frozen", False)
        if latest_v > current_v and binary_url:
            preflight = _preflight_check(binary_url=binary_url)
            result["preflight"] = preflight
            if frozen:
                update_state.update_ready = True
                update_state.latest_version = tag
                update_state.binary_url = binary_url
                update_state.expected_sha256 = expected_sha256
                result.update({
                    "update_ready": True,
                    "latest": tag,
                    "body": body,
                    "frozen": True,
                    "source_url": source_url,
                    "preflight_pass": preflight["pass"],
                })
            else:
                file_logger.info("Update %s available (binary) — dev mode, skipping auto-install", tag)
                result.update({
                    "update_ready": True,
                    "latest": tag,
                    "body": body,
                    "frozen": False,
                    "source_url": source_url,
                    "hint": "Development mode: run 'git pull' or download source from the release page.",
                })
        else:
            file_logger.info("Update tag %s exists, but binary for OS is missing/building. Deferring.", tag)
    except Exception as e:
        file_logger.warning(f"Background updates repo search query failed: {e}")
        result["error"] = str(e)

    update_state.last_check_time = time.monotonic()
    update_state.current_check_result = result
    update_state.preflight_pass = result.get("preflight", {}).get("pass", False)
    update_state.preflight_result = result.get("preflight", {})
    update_state.release_body = result.get("body", "")
    return result


def download_update_worker(expected_sha256: str = "") -> None:
    if not getattr(sys, "frozen", False):
        update_state.error = "Binary updates are not supported in development mode. Use 'git pull' to update."
        update_state.success = False
        update_state.is_downloading = False
        return

    preflight = _preflight_check(binary_url=update_state.binary_url)
    if not preflight["pass"]:
        failed = [k for k, v in preflight["checks"].items() if v is False]
        update_state.error = f"Pre-flight checks failed: {', '.join(failed)}"
        update_state.success = False
        update_state.is_downloading = False
        return

    dest_dir = _tempfile.mkdtemp(prefix="audit_update_")
    try:
        update_state.is_downloading = True
        update_state.progress_pct = 0.0
        update_state.success = False
        update_state.error = ""

        dest_archive = os.path.join(dest_dir, "update.pkg")
        update_state.dest_zip_path = dest_archive

        def progress_cb(pct: float) -> None:
            update_state.progress_pct = pct

        _download_update(update_state.binary_url, dest_archive, progress_cb)

        if expected_sha256:
            actual = _sha256_file(dest_archive)
            if actual != expected_sha256:
                raise RuntimeError(f"SHA256 mismatch: expected {expected_sha256}, got {actual}")

        install_dir = _get_install_dir()
        bat = _install_binary_update(dest_archive, install_dir, log_callback=file_logger.info)
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

threading.Thread(target=_background_check_worker, daemon=True, name="update-bg-checker").start()
