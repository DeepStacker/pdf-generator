from __future__ import annotations
import sys
import glob as glob_mod
from pathlib import Path
from typing import Any

from .config import SourceConfig, ProcessingContext, PT_COLUMNS, MD_COLUMNS
from .extractor import SourceExtractor, ExtractorError
from .mapper import DataMapper, MappingError
from .writer import ConsolidatedWriter
from .audit import AuditLog


class Consolidator:
    """Main orchestrator: extract → map → write all source files."""

    def __init__(
        self,
        template_path: Path,
        source_dir: Path,
        output_path: Path,
        audit_dir: Path | None = None,
        context: ProcessingContext | None = None,
        merge_mode: bool = False,
    ):
        self.template_path = template_path
        self.source_dir = source_dir
        self.output_path = output_path
        self.context = context or ProcessingContext()
        self.audit = AuditLog(output_dir=audit_dir)
        self.writer = ConsolidatedWriter(template_path)
        self._pt_last = 0
        self._md_last = 0
        self.merge_mode = merge_mode
        self.merge_stats: dict = {"new_rows": 0, "new_sources": 0, "existing_rows": 0}

    def _load_existing_excel(self) -> tuple[list[dict[int, Any]], list[dict[int, Any]]]:
        """Load existing PT and MD rows from a previous consolidated output as dicts keyed by column index."""
        import openpyxl
        existing_pt: list[dict[int, Any]] = []
        existing_md: list[dict[int, Any]] = []
        if not self.output_path.exists():
            return existing_pt, existing_md

        try:
            wb = openpyxl.load_workbook(self.output_path, data_only=True)
            if "Payment Tracker" in wb.sheetnames:
                ws = wb["Payment Tracker"]
                for row in ws.iter_rows(min_row=2, values_only=True):
                    rd: dict[int, Any] = {}
                    for ci, val in enumerate(row):
                        if val is not None:
                            rd[ci] = val
                    if rd:
                        existing_pt.append(rd)
            if "Master Data" in wb.sheetnames:
                ws = wb["Master Data"]
                for row in ws.iter_rows(min_row=2, values_only=True):
                    rd = {}
                    for ci, val in enumerate(row):
                        if val is not None:
                            rd[ci] = val
                    if rd:
                        existing_md.append(rd)
            wb.close()
        except Exception:
            pass
        return existing_pt, existing_md

    # Assayer Code column indices (0-based) in canonical column order
    _PT_ASSY_CODE_IDX = 3   # "Assayer Code" in PT_COLUMNS
    _MD_ASSY_CODE_IDX = 10  # "Assayer Code" in MD_COLUMNS

    def _merge_pt_rows(self, new_rows: list[dict[int, Any]], existing_rows: list[dict[int, Any]]) -> list[dict[int, Any]]:
        """Merge new PT rows into existing, skipping duplicates by Assayer Code."""
        if not existing_rows:
            return new_rows

        existing_codes: set[str] = set()
        for row in existing_rows:
            code = str(row.get(self._PT_ASSY_CODE_IDX, "")).strip()
            if code:
                existing_codes.add(code)

        merged = list(existing_rows)
        added = 0
        for row in new_rows:
            code = str(row.get(self._PT_ASSY_CODE_IDX, "")).strip()
            if not code or code not in existing_codes:
                merged.append(row)
                added += 1
                if code:
                    existing_codes.add(code)

        self.merge_stats["existing_rows"] = len(existing_rows)
        self.merge_stats["new_rows"] = added
        return merged

    def _merge_md_rows(self, new_rows: list[dict[int, Any]], existing_rows: list[dict[int, Any]]) -> list[dict[int, Any]]:
        """Merge new MD rows into existing, skipping duplicates by Assayer Code."""
        if not existing_rows:
            return new_rows

        existing_codes: set[str] = set()
        for row in existing_rows:
            code = str(row.get(self._MD_ASSY_CODE_IDX, "")).strip()
            if code:
                existing_codes.add(code)

        merged = list(existing_rows)
        for row in new_rows:
            code = str(row.get(self._MD_ASSY_CODE_IDX, "")).strip()
            if not code or code not in existing_codes:
                merged.append(row)
                if code:
                    existing_codes.add(code)

        self.merge_stats["existing_rows"] += len(existing_rows)
        return merged

    def run(self, source_configs: list[SourceConfig]) -> int:
        has_errors = False

        for config in source_configs:
            try:
                self._process_source(config)
            except (ExtractorError, MappingError, ValueError) as e:
                self.audit.log(str(e), level="ERROR")
                print(f"  ERROR: {e}", file=sys.stderr)
                has_errors = True
            except Exception as e:
                self.audit.log(f"Unexpected error: {e}", level="ERROR")
                print(f"  UNEXPECTED ERROR: {e}", file=sys.stderr)
                has_errors = True

        # Incremental merge: load existing output and merge with new rows
        if self.merge_mode:
            existing_pt, existing_md = self._load_existing_excel()
            if existing_pt or existing_md:
                print(f"\n Merge mode: loaded {len(existing_pt)} existing PT rows, {len(existing_md)} existing MD rows")
                self.writer.pt_rows = self._merge_pt_rows(self.writer.pt_rows, existing_pt)
                self.writer.md_rows = self._merge_md_rows(self.writer.md_rows, existing_md)
                self.merge_stats["existing_rows"] = self.merge_stats.get("existing_rows", 0)
                self.merge_stats["new_sources"] = 1  # signal that merge occurred
                print(f"  Merged: {len(self.writer.pt_rows)} PT rows, {len(self.writer.md_rows)} MD rows")

        if has_errors:
            print("\n Some sources had errors. Check audit report for details.")
        else:
            print("\n All sources processed successfully.")

        try:
            result = self.writer.write(self.output_path)
            print(f" Consolidated output: {result}")
            self._write_error = None
        except Exception as e:
            msg = f"Failed to write output: {e}"
            self.audit.log(msg, level="ERROR")
            print(f"  ERROR writing output: {e}", file=sys.stderr)
            self._write_error = str(e)
            has_errors = True

        try:
            audit_file = self.audit.write_report()
            print(f" Audit report: {audit_file}")
        except Exception as e:
            print(f"  Warning: Could not write audit report: {e}", file=sys.stderr)

        return 1 if has_errors else 0

    def _process_source(self, config: SourceConfig):
        pattern = str(self.source_dir / config.file_pattern)
        matches = sorted(glob_mod.glob(pattern))
        if not matches:
            raise ExtractorError(
                f"No file matching '{config.file_pattern}' in {self.source_dir}"
            )

        filepath = Path(matches[0])
        self.audit.start_source(filepath.name)
        print(f"\nProcessing: {filepath.name}")

        extractor = SourceExtractor(filepath, config)
        hidden = extractor.get_hidden_sheets()
        if hidden:
            msg = f"Hidden sheets: {hidden}"
            self.audit.log(msg, level="INFO", source=filepath.name)
            print(f"  i {msg}")

        pt_extracted = extractor.extract_sheet(
            config.pt_sheet_hint,
            header_row=config.header_row,
            data_start_row=config.data_start_row,
        )
        print(f"  PT: {len(pt_extracted)} rows extracted")

        md_extracted = extractor.extract_sheet(
            config.md_sheet_hint,
            header_row=config.header_row,
            data_start_row=config.data_start_row,
        )

        if config.exclude_md_names:
            before = len(md_extracted.rows)
            names_set = set(config.exclude_md_names)
            md_extracted.rows = [
                r for r in md_extracted.rows
                if not any(
                    isinstance(v, str) and v.strip() in names_set
                    for v in r.values()
                )
            ]
            after = len(md_extracted.rows)
            if before != after:
                print(f"  Excluded {before - after} MD row(s) by name filter")

        print(f"  MD: {len(md_extracted)} rows extracted")

        if config.expected_pt_rows:
            lo, hi = config.expected_pt_rows
            if not (lo <= len(pt_extracted) <= hi):
                self.audit.log(
                    f"PT row count {len(pt_extracted)} outside [{lo}, {hi}]",
                    level="WARNING", source=filepath.name,
                )

        if config.expected_md_rows:
            lo, hi = config.expected_md_rows
            if not (lo <= len(md_extracted) <= hi):
                self.audit.log(
                    f"MD row count {len(md_extracted)} outside [{lo}, {hi}]",
                    level="WARNING", source=filepath.name,
                )

        mapper = DataMapper(config, self.audit, context=self.context)
        mapper.set_start_counters(self._pt_last, self._md_last)

        pt_mapped = mapper.map_pt(pt_extracted, filepath.name)
        md_mapped = mapper.map_md(md_extracted, filepath.name)

        # Auto-derive missing State/Zone from Location
        pt_mapped = DataMapper.derive_state_zone(
            pt_mapped, "PT", self.audit, PT_COLUMNS,
            location_col="Location", state_col="State", zone_col="Zone",
        )
        md_mapped = DataMapper.derive_state_zone(
            md_mapped, "MD", self.audit, MD_COLUMNS,
            location_col="Location ", state_col="State", zone_col="Zone",
        )

        # Normalize all dates to dd-mm-yyyy format
        pt_mapped = DataMapper.normalize_dates(pt_mapped)
        md_mapped = DataMapper.normalize_dates(md_mapped)

        self._pt_last = getattr(mapper, "pt_counter", self._pt_last)
        self._md_last = getattr(mapper, "md_counter", self._md_last)

        for row in pt_mapped:
            code = row.get(PT_COLUMNS.index("Assayer Code"))
            name = row.get(PT_COLUMNS.index("Assayer Name"))
            if code:
                self.audit.check_assayer_duplicate(
                    str(code), str(name or ""), config.client_name, filepath.name
                )

        self.writer.add_pt_rows(pt_mapped)
        self.writer.add_md_rows(md_mapped)

        self.audit.record_row_counts(filepath.name, len(pt_mapped), len(md_mapped))

        needs_manual = config.needs_manual_enrichment
        if needs_manual:
            for col, desc in needs_manual.items():
                self.audit.log(f"  Manual enrichment needed: {col} - {desc}", level="INFO")

        self.audit.finish_source(filepath.name)
        print(f"  Added {len(pt_mapped)} PT rows, {len(md_mapped)} MD rows")
