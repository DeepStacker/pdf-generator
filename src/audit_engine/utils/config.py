"""Application configuration — single source of truth for paths and settings."""

import os
from dataclasses import dataclass, field
from typing import Final


@dataclass(frozen=True)
class Paths:
    log: str = field(default_factory=lambda: os.environ.get("AUDIT_ENGINE_LOG_PATH") or os.path.join(os.path.expanduser("~"), ".idfc_audit_engine.log"))
    db: str = field(default_factory=lambda: os.environ.get("AUDIT_ENGINE_DB_PATH") or os.path.join(os.path.expanduser("~"), ".idfc_pdf_generator_v3.db"))


@dataclass(frozen=True)
class BankFingerprints:
    idfc: frozenset[str] = frozenset({"prospectno", "cuid", "tare weight", "currentbranch"})
    equitas: frozenset[str] = frozenset({"svs_loan_no", "sole_id", "branch_name", "loan no"})
    arvog: frozenset[str] = frozenset({"jewellery1", "jewellery2"})


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
update: Final[UpdateConfig] = UpdateConfig()
ui: Final[UIConfig] = UIConfig()
heartbeat: Final[HeartbeatConfig] = HeartbeatConfig()
