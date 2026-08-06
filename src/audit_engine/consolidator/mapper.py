from __future__ import annotations
import re
from typing import Any

from .config import (
    SourceConfig,
    PT_COLUMNS,
    MD_COLUMNS,
    DEFAULT_VALUES,
    HEADER_PATTERNS,
    AUTO_COLUMNS,
    ProcessingContext,
)
from .extractor import ExtractedSheet
from .audit import AuditLog
from .geography import location_to_state_and_zone, state_to_zone


class MappingError(Exception):
    """Raised when mapping cannot proceed."""


def _normalize(name: str) -> str:
    n = name.lower().strip()
    n = re.sub(r"\s+", " ", n)
    n = re.sub(r"[^a-z0-9 /]", "", n)
    return n.strip()


def _match_source_header(
    canonical_name: str,
    source_headers: list[str],
    used_headers: dict[str, str],
) -> str | None:
    """Find best source header matching any pattern for this canonical column.

    - Skips headers claimed by the *same* canonical name (same-name exclusion).
    - Allows sharing with a *different* canonical name.
    - Picks highest-scoring match (longer pattern, shorter header).
    """
    patterns = HEADER_PATTERNS.get(canonical_name, [canonical_name])
    best_match: str | None = None
    best_score: tuple[int, int] = (0, 0)
    for pattern in patterns:
        p_norm = _normalize(pattern)
        p_len = len(p_norm)
        for sh in source_headers:
            claimant = used_headers.get(sh)
            # Same canonical name cannot share → skip
            if claimant is not None and claimant == canonical_name:
                continue
            sh_norm = _normalize(sh)
            if p_norm in sh_norm:
                score = (p_len, -len(sh_norm))
                if score > best_score:
                    best_match = sh
                    best_score = score
    return best_match


class DataMapper:
    """Applies generic header-pattern matching to transform extracted data."""

    def __init__(
        self,
        config: SourceConfig,
        audit: AuditLog,
        context: ProcessingContext | None = None,
    ):
        self.config = config
        self.audit = audit
        self.context = context or ProcessingContext()
        self.pt_counter = 0
        self.md_counter = 0

    def set_start_counters(self, pt_last: int = 0, md_last: int = 0):
        self.pt_counter = pt_last
        self.md_counter = md_last

    def map_pt(self, extracted: ExtractedSheet, filename: str) -> list[dict[int, Any]]:
        return self._map_sheet(
            extracted=extracted,
            canonical_schema=PT_COLUMNS,
            counter_attr="pt_counter",
            source_type="PT",
            filename=filename,
        )

    def map_md(self, extracted: ExtractedSheet, filename: str) -> list[dict[int, Any]]:
        return self._map_sheet(
            extracted=extracted,
            canonical_schema=MD_COLUMNS,
            counter_attr="md_counter",
            source_type="MD",
            filename=filename,
        )

    def _map_sheet(
        self,
        extracted: ExtractedSheet,
        canonical_schema: list[str],
        counter_attr: str,
        source_type: str,
        filename: str,
    ) -> list[dict[int, Any]]:
        if not extracted:
            self.audit.log(f"{source_type}: No data extracted, skipping")
            return []

        defaults_used: set[str] = set()
        unmatched_canonicals: list[str] = []
        overrides_used: set[str] = set()
        overrides = self.config.column_overrides

        # Pre-match: for each canonical, determine which source header to use.
        header_map: dict[int, str | None] = {}
        used_source_headers: dict[str, str] = {}  # source_header -> first claimant canonical name
        mappings_recorded = []

        # Build processing order: longer max-pattern canonicals first
        # (more specific match), ties broken by schema index.
        scored: list[tuple[int, int, str]] = []  # (neg_max_plen, schema_idx, schema_col)
        for schema_idx, schema_col in enumerate(canonical_schema):
            if schema_col in AUTO_COLUMNS:
                header_map[schema_idx] = None
                mappings_recorded.append({
                    "canonical_col": schema_col,
                    "schema_idx": schema_idx,
                    "mapped_header": None,
                    "match_type": "auto"
                })
                continue
            if schema_col in overrides:
                header_map[schema_idx] = overrides[schema_col]
                overrides_used.add(schema_col)
                mappings_recorded.append({
                    "canonical_col": schema_col,
                    "schema_idx": schema_idx,
                    "mapped_header": overrides[schema_col],
                    "match_type": "override"
                })
                continue
            patterns = HEADER_PATTERNS.get(schema_col, [schema_col])
            max_plen = max((len(_normalize(p)) for p in patterns), default=0)
            scored.append((-max_plen, schema_idx, schema_col))
        scored.sort()  # more specific first, then schema index

        for _, schema_idx, schema_col in scored:
            actual = _match_source_header(schema_col, extracted.headers, used_source_headers)
            if actual:
                if actual not in used_source_headers:
                    used_source_headers[actual] = schema_col
                header_map[schema_idx] = actual
                mappings_recorded.append({
                    "canonical_col": schema_col,
                    "schema_idx": schema_idx,
                    "mapped_header": actual,
                    "match_type": "pattern"
                })
            else:
                header_map[schema_idx] = None
                unmatched_canonicals.append(schema_col)
                mappings_recorded.append({
                    "canonical_col": schema_col,
                    "schema_idx": schema_idx,
                    "mapped_header": None,
                    "match_type": "default"
                })

        self.audit.record_mappings(filename, source_type, mappings_recorded)

        canonical_rows: list[dict[int, Any]] = []

        for row_idx, src_row in enumerate(extracted.rows):
            counter = getattr(self, counter_attr, 0)
            canonical: dict[int, Any] = {}

            for schema_idx, schema_col in enumerate(canonical_schema):
                if schema_col in AUTO_COLUMNS:
                    if schema_col in ("S.no", "Sr No"):
                        counter += 1
                        canonical[schema_idx] = counter
                    elif schema_col in ("client", "Client"):
                        canonical[schema_idx] = self.config.client_name
                    elif schema_col == "Month":
                        canonical[schema_idx] = self.context.get("audit_month", "")
                    continue

                source_hdr = header_map.get(schema_idx)
                if source_hdr is None:
                    dflt = DEFAULT_VALUES.get(schema_col)
                    canonical[schema_idx] = dflt if dflt is not None else None
                    continue

                val = src_row.get(source_hdr)
                if val is not None:
                    canonical[schema_idx] = val
                else:
                    dflt = DEFAULT_VALUES.get(schema_col)
                    if dflt is not None:
                        canonical[schema_idx] = dflt
                        defaults_used.add(schema_col)
                    else:
                        canonical[schema_idx] = None

            setattr(self, counter_attr, counter)
            canonical_rows.append(canonical)

        # Accumulate financial sums
        FINANCIAL_COLS = {
            "Base Audit Fee", "Total pay (Base)", " Travel charges(If any)",
            "Cancelled visits", "Branch Cancellation Charges",
            " Andaman & Nicobar Branch Expenses", "Error Deduction", "Total pay",
            "Client fee", "Additional", "Final Client Fees",
            "Assayer fee", "Additional fee", "Cancelled", "Error Deduciton", "Total",
            "Total pouches suggested for audit", "Already Audited", "A/C Closed",
            "A/C Auctioned", "Packet Missing",
            "Actual Audited (except already audited & A/C closed) ",
            "Extra audited pouches", "Total No.of packets actually audited"
        }
        financials = {}
        for schema_idx, schema_col in enumerate(canonical_schema):
            if schema_col in FINANCIAL_COLS:
                total_sum = 0.0
                for r in canonical_rows:
                    val = r.get(schema_idx)
                    if val is not None:
                        try:
                            cleaned = str(val).replace(",", "").strip()
                            if cleaned:
                                total_sum += float(cleaned)
                        except ValueError:
                            pass
                # Keep index as well to support duplicate canonical columns
                financials[f"{schema_col}___{schema_idx}"] = total_sum

        self.audit.record_financials(filename, source_type, financials)

        # Log unmapped source columns (once)
        all_mapped = set(h for h in header_map.values() if h is not None)
        unmapped = [h for h in extracted.headers if h.strip() and h not in all_mapped]
        if unmapped:
            self.audit.log(
                f"{source_type}: Unmapped source columns: {unmapped}",
                level="INFO",
            )

        if defaults_used:
            self.audit.log(
                f"{source_type}: Defaults applied for: {sorted(set(defaults_used))}",
                level="INFO",
            )

        if unmatched_canonicals:
            unique_unmatched = list(set(unmatched_canonicals))
            self.audit.log(
                f"{source_type}: Canonical columns not found in source (using defaults): "
                f"{unique_unmatched}",
                level="INFO",
            )

        if overrides_used:
            self.audit.log(
                f"{source_type}: Column overrides applied: {sorted(overrides_used)}",
                level="INFO",
            )

        return canonical_rows

    @staticmethod
    def normalize_dates(
        rows: list[dict[int, Any]],
        date_format: str = "%d-%m-%Y",
    ) -> list[dict[int, Any]]:
        from datetime import datetime, date as date_type
        for row in rows:
            for k, v in row.items():
                if isinstance(v, (datetime, date_type)):
                    row[k] = v.strftime(date_format)
        return rows

    @staticmethod
    def derive_state_zone(
        rows: list[dict[int, Any]],
        source_type: str,
        audit: AuditLog,
        schema: list[str],
        location_col: str = "Location",
        state_col: str = "State",
        zone_col: str = "Zone",
    ) -> list[dict[int, Any]]:
        loc_idx = schema.index(location_col) if location_col in schema else None
        state_idx = schema.index(state_col) if state_col in schema else None
        zone_idx = schema.index(zone_col) if zone_col in schema else None
        if loc_idx is None:
            return rows

        derived_count = 0
        for row in rows:
            loc = row.get(loc_idx)
            if state_idx is not None:
                state = row.get(state_idx)
            else:
                state = None
            if zone_idx is not None:
                zone = row.get(zone_idx)
            else:
                zone = None

            if (state_idx is not None) and (not state) and loc:
                derived_state, derived_zone = location_to_state_and_zone(loc)
                if derived_state:
                    row[state_idx] = derived_state
                    derived_count += 1
                    state = derived_state
                if derived_zone and (zone_idx is not None) and (not zone):
                    row[zone_idx] = derived_zone

            if (zone_idx is not None) and (not zone) and state:
                z = state_to_zone(state)
                if z:
                    row[zone_idx] = z

        if derived_count > 0:
            audit.log(
                f"{source_type}: Derived State/Zone from Location for "
                f"{derived_count} rows",
                level="INFO",
            )

        return rows
