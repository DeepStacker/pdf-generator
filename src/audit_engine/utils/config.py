"""Application configuration — single source of truth for paths and settings.

Path resolution order for database and log files:
1. Environment variable override (AUDIT_ENGINE_DB_PATH / AUDIT_ENGINE_LOG_PATH)
2. User home directory (~/.idfc_pdf_generator_v3.db)
3. Portable mode: next to executable (for frozen PyInstaller binaries)
4. System temp directory (last resort, always writable)
"""

import contextlib
import json
import logging
import os
import sys
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final

_logger = logging.getLogger(__name__)


def _is_unsafe_vm_or_net_path(path: str) -> bool:
    """Check if a path is on an unsafe VM shared folder or network share.

    SQLite has locking/I/O issues on network drives and shared filesystems.
    Windows WebViews block script execution from UNC paths.
    """
    path_lower = path.lower()
    return path.startswith(("\\\\", "//")) or "/media/psf" in path_lower or "/mnt/psf" in path_lower or "prl_fs" in path_lower


def _get_platform_local_dir() -> str | None:
    """Return the standard platform-specific local data directory, or None."""
    # Windows: Local AppData is local (not shared via Parallels by default)
    if sys.platform == "win32":
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata and os.path.isdir(local_appdata):
            return os.path.join(local_appdata, "AuditEngineElite")
        appdata = os.environ.get("APPDATA")
        if appdata and os.path.isdir(appdata):
            return os.path.join(appdata, "AuditEngineElite")

    # macOS: Local Application Support
    elif sys.platform == "darwin":
        home = os.path.expanduser("~")
        if home and not _is_unsafe_vm_or_net_path(home):
            return os.path.join(home, "Library", "Application Support", "AuditEngineElite")

    # Linux: Local Share
    else:
        home = os.path.expanduser("~")
        if home and not _is_unsafe_vm_or_net_path(home):
            return os.path.join(home, ".local", "share", "AuditEngineElite")

    return None


def _resolve_writable_path(filename: str, env_var: str) -> str:
    """Resolve a writable file path with multiple fallback locations.

    This ensures the app works even on locked-down corporate systems
    where certain directories may be read-only or on network drives.
    """
    # 1. Environment variable override (highest priority)
    env_path = os.environ.get(env_var)
    if env_path:
        env_dir = os.path.dirname(env_path) or "."
        try:
            os.makedirs(env_dir, exist_ok=True)
            if os.path.isdir(env_dir) and os.access(env_dir, os.W_OK):
                return env_path
        except Exception:
            pass

    # 2. Platform-specific local data directory (guaranteed local to guest OS/VM, avoiding VM shared folders)
    local_dir = _get_platform_local_dir()
    if local_dir:
        try:
            os.makedirs(local_dir, exist_ok=True)
            if os.path.isdir(local_dir) and os.access(local_dir, os.W_OK):
                return os.path.join(local_dir, filename)
        except Exception:
            pass

    # 3. User home directory (standard location, if not a network/VM share)
    home = os.path.expanduser("~")
    if home and not _is_unsafe_vm_or_net_path(home):
        try:
            os.makedirs(home, exist_ok=True)
            if os.path.isdir(home) and os.access(home, os.W_OK):
                return os.path.join(home, filename)
        except Exception:
            pass

    # 4. Portable mode: next to executable (PyInstaller frozen binary)
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        if exe_dir and not _is_unsafe_vm_or_net_path(exe_dir):
            try:
                os.makedirs(exe_dir, exist_ok=True)
                if os.path.isdir(exe_dir) and os.access(exe_dir, os.W_OK):
                    return os.path.join(exe_dir, filename)
            except Exception:
                pass

    # 5. System temp directory (always writable for standard users)
    temp_dir = tempfile.gettempdir()
    with contextlib.suppress(Exception):
        os.makedirs(temp_dir, exist_ok=True)
    return os.path.join(temp_dir, filename)


@dataclass(frozen=True)
class Paths:
    log: str = field(default_factory=lambda: _resolve_writable_path(".idfc_audit_engine.log", "AUDIT_ENGINE_LOG_PATH"))
    db: str = field(default_factory=lambda: _resolve_writable_path(".idfc_pdf_generator_v3.db", "AUDIT_ENGINE_DB_PATH"))


@dataclass(frozen=True)
class BankFingerprints:
    idfc: frozenset[str] = frozenset({"prospectno", "cuid", "tare weight", "currentbranch"})
    equitas: frozenset[str] = frozenset({"svs_loan_no", "sole_id", "branch_name", "loan no"})
    arvog: frozenset[str] = frozenset({"jewellery1", "jewellery2", "jewellery no.", "packets number"})


# Region -> cluster manager fallback for Arvog master sheets that leave the
# "Cluster Manager" column blank. Kept here rather than in the service so a
# staffing change is a config edit, not a code change: set
# ARVOG_CLUSTER_MANAGERS='{"WARANGAL": "Some Name"}' to override, or to '{}'
# to switch the fallback off entirely.
_DEFAULT_REGION_CLUSTER_MANAGERS: Final[dict[str, str]] = {"WARANGAL": "D.Praveen Kumar"}


def _load_region_cluster_managers() -> Mapping[str, str]:
    raw = os.environ.get("ARVOG_CLUSTER_MANAGERS", "").strip()
    if not raw:
        return MappingProxyType(dict(_DEFAULT_REGION_CLUSTER_MANAGERS))
    try:
        parsed = json.loads(raw)
    except ValueError:
        _logger.warning("ARVOG_CLUSTER_MANAGERS is not valid JSON; using built-in defaults")
        return MappingProxyType(dict(_DEFAULT_REGION_CLUSTER_MANAGERS))
    if not isinstance(parsed, dict):
        _logger.warning("ARVOG_CLUSTER_MANAGERS must be a JSON object; using built-in defaults")
        return MappingProxyType(dict(_DEFAULT_REGION_CLUSTER_MANAGERS))
    # Regions are matched upper-cased and trimmed, the same way the sheet value is.
    return MappingProxyType({
        str(region).strip().upper(): str(name).strip()
        for region, name in parsed.items()
        if str(name).strip()
    })


@dataclass(frozen=True)
class ArvogConfig:
    """Arvog-specific defaults that are staffing data rather than logic."""

    region_cluster_managers: Mapping[str, str] = field(default_factory=_load_region_cluster_managers)

    def cluster_manager_for(self, region: str | None) -> str | None:
        """Return the standing cluster manager for a region, or None."""
        if not region:
            return None
        return self.region_cluster_managers.get(str(region).strip().upper())


@dataclass(frozen=True)
class UpdateConfig:
    repo: str = "DeepStacker/pdf-generator"
    github_api: str = "https://api.github.com/repos/DeepStacker/pdf-generator/releases/latest"


@dataclass(frozen=True)
class UIConfig:
    max_recent_files: int = 8


@dataclass(frozen=True)
class HeartbeatConfig:
    timeout: int = 120
    interval: int = 15


# Global singleton instances
paths: Final[Paths] = Paths()
fingerprints: Final[BankFingerprints] = BankFingerprints()
arvog: Final[ArvogConfig] = ArvogConfig()
update: Final[UpdateConfig] = UpdateConfig()
ui: Final[UIConfig] = UIConfig()
heartbeat: Final[HeartbeatConfig] = HeartbeatConfig()
