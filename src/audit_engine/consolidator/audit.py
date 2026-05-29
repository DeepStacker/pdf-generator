from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import Any


class AuditLog:
    """Structured audit log of every mapping decision.

    Records:
      - Which source files were processed
      - How many PT and MD rows were added
      - Which columns were enriched, defaulted, or dropped
      - Any warnings or errors encountered
      - Cross-source duplicate assayer codes
    """

    def __init__(self, output_dir: Path | str | None = None):
        self.output_dir = Path(output_dir) if output_dir else None
        self.entries: list[dict[str, Any]] = []
        self.source_logs: dict[str, dict[str, Any]] = {}
        self.warnings: list[str] = []
        self.errors: list[str] = []
        self._assayer_codes_seen: dict[str, str] = {}  # code → client_name
        self._cross_duplicates: list[dict[str, str]] = []

    def log(
        self,
        message: str,
        level: str = "INFO",
        source: str | None = None,
        data: Any = None,
    ):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "source": source,
        }
        if data is not None:
            entry["data"] = data
        self.entries.append(entry)

        if level == "WARNING":
            self.warnings.append(message)
        elif level == "ERROR":
            self.errors.append(message)

    def start_source(self, filename: str):
        self.source_logs[filename] = {
            "filename": filename,
            "pt_rows": 0,
            "md_rows": 0,
            "pt_mappings": [],
            "md_mappings": [],
            "pt_financials": {},
            "md_financials": {},
            "enriched_columns": [],
            "defaulted_columns": [],
            "extras_columns": [],
            "warnings": [],
            "status": "processing",
        }
        self.log(f"Started processing: {filename}")

    def record_row_counts(self, filename: str, pt_rows: int, md_rows: int):
        if filename in self.source_logs:
            self.source_logs[filename]["pt_rows"] = pt_rows
            self.source_logs[filename]["md_rows"] = md_rows

    def record_mappings(self, filename: str, sheet_type: str, mappings: list[dict[str, Any]]):
        if filename in self.source_logs:
            self.source_logs[filename][f"{sheet_type.lower()}_mappings"] = mappings

    def record_financials(self, filename: str, sheet_type: str, financials: dict[str, float]):
        if filename in self.source_logs:
            self.source_logs[filename][f"{sheet_type.lower()}_financials"] = financials

    def record_enrichments(self, filename: str, columns: list[str]):
        if filename in self.source_logs:
            self.source_logs[filename]["enriched_columns"].extend(columns)

    def record_defaults(self, filename: str, columns: list[str]):
        if filename in self.source_logs:
            self.source_logs[filename]["defaulted_columns"].extend(columns)

    def record_extras(self, filename: str, columns: list[str]):
        if filename in self.source_logs:
            self.source_logs[filename]["extras_columns"].extend(columns)

    def check_assayer_duplicate(
        self,
        code: str,
        name: str,
        client: str,
        filename: str,
    ):
        """Track assayer codes across sources; log duplicates."""
        if code in self._assayer_codes_seen:
            prev_client = self._assayer_codes_seen[code]
            dup = {
                "assayer_code": code,
                "assayer_name": name,
                "source_1_client": prev_client,
                "source_1_file": filename,
                "source_2_client": client,
            }
            self._cross_duplicates.append(dup)
            self.log(
                f"Cross-source duplicate assayer: {name} ({code}) "
                f"appears in both {prev_client} and {client}",
                level="WARNING",
                source=filename,
            )
        else:
            self._assayer_codes_seen[code] = client

    def finish_source(self, filename: str, status: str = "completed"):
        if filename in self.source_logs:
            self.source_logs[filename]["status"] = status
        self.log(f"Finished processing: {filename}", source=filename)

    def summary(self) -> dict[str, Any]:
        total_pt = sum(
            s.get("pt_rows", 0) for s in self.source_logs.values()
        )
        total_md = sum(
            s.get("md_rows", 0) for s in self.source_logs.values()
        )
        return {
            "timestamp": datetime.now().isoformat(),
            "sources_processed": len(self.source_logs),
            "status": "completed with errors" if self.errors else "completed",
            "total_pt_rows": total_pt,
            "total_md_rows": total_md,
            "warnings_count": len(self.warnings),
            "errors_count": len(self.errors),
            "errors": self.errors,
            "warnings": self.warnings,
            "cross_source_duplicates": len(self._cross_duplicates),
            "sources": list(self.source_logs.values()),
            "cross_duplicates": self._cross_duplicates,
        }

    def write_report(self, output_path: Path | None = None) -> Path:
        path = output_path or (
            self.output_dir / "consolidation_audit.json"
            if self.output_dir
            else Path("consolidation_audit.json")
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.summary(), f, indent=2, default=str)
        self.log(f"Audit report written to: {path}")
        return path
