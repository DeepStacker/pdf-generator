"""Domain data models and DTOs."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GenerationRequest:
    """A request to generate PDF reports from a bank Excel file."""
    bank: str
    filepath: str | list[str]
    out_path: str
    auto_open: bool = True
    naming_pattern: str = "{branch}_{type}"
    audit_type: str = "POA"
    output_mode: str = "BOTH"
    equitas_stage: str = "STAGE 1"
    equitas_format: str = "BOTH"
    equitas_pack: str = "FOLDER"
    column_mappings: dict[str, str] | None = None


@dataclass(frozen=True)
class GenerationResult:
    """Result of a PDF generation run."""
    success: bool
    files_processed: int = 0
    items_generated: int = 0
    total_time_seconds: float = 0.0
    total_size_bytes: int = 0
    error: str | None = None
    title: str = ""


@dataclass
class ProgressInfo:
    """Current progress of a running generation task."""
    pct: float = 0.0
    active_branch: str = ""
    logs: list[dict] = field(default_factory=list)
    is_running: bool = False
    summary: dict | None = None
    cancel_requested: bool = False


@dataclass(frozen=True)
class ValidationResult:
    """Result of Excel file validation."""
    valid: bool
    error: str = ""
    detected_bank: str | None = None
    rows: int = 0
    branches: int = 0
    headers: list[str] = field(default_factory=list)
    preview: list[list[str]] = field(default_factory=list)


@dataclass(frozen=True)
class BankProfile:
    """Bank metadata for auto-detection and display."""
    name: str
    fingerprint_columns: frozenset[str]
    fingerprint_threshold: int
    display_color: str = ""

    def matches(self, headers: set[str]) -> bool:
        return len(self.fingerprint_columns & headers) >= self.fingerprint_threshold


@dataclass(frozen=True)
class HistoryEntry:
    """A single history record."""
    id: int = 0
    timestamp: str = ""
    excel_name: str = ""
    pdf_count: int = 0
    output_path: str = ""
    audit_type: str = ""
    full_path: str = ""
