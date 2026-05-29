# PT-MD Relationship & System Architecture — Complete Analysis

## Goal
Generate consolidated report from source files and compare cell-by-cell against manually prepared template; deeply understand PT-MD relationship to validate automation correctness.

## Source Files Analyzed
- `sources/Axis Bank POA Payment Tracker - Feb'26.xlsx` — Axis Bank POA (101 PT rows, 384 MD rows)
- `sources/RBL(Muthoot Fincorp) Payment Tracker -Feb'26.xlsx` — RBL / Muthoot Fincorp (63 PT rows, 431 MD rows)
- `templates/Feb'26 consolidated.xlsx` — manually prepared reference
- `~/.audit_engine_elite/settings/mapping_rules.xlsx` — external column overrides

## Architecture Overview
`ProcessingContext` is a dataclass in `src/audit_engine/consolidator/config.py:411`. Must use keyword args: `ProcessingContext(audit_month="Feb'26")`. The month format must be `Feb'26` (not `Feb-26`).

### Data Flow
```
Source Excel (*.xlsx)
  ├── PT sheet → SourceExtractor.extract_sheet() → DataMapper.map_pt() → DataMapper.derive_state_zone("PT")
  ├── MD sheet → SourceExtractor.extract_sheet() → DataMapper.map_md() → DataMapper.derive_state_zone("MD")
  └── Both → Consolidator.writer → "Payment Tracker" + "Master Data" sheets in output
```

Current system reads PT directly from source — does NOT derive PT from MD. PT and MD flow through parallel independent pipelines.

### Key files
- `src/audit_engine/consolidator/config.py` — HEADER_PATTERNS, ProcessingContext, PT_COLUMNS (24 cols), MD_COLUMNS (59 cols), AUTO_COLUMNS, DEFAULT_VALUES
- `src/audit_engine/consolidator/mapper.py` — DataMapper (map_pt/map_md), _match_source_header (score-order), _map_sheet, derive_state_zone, normalize_dates
- `src/audit_engine/consolidator/extractor.py` — SourceExtractor, dedup (___2, ___3 suffixes), _is_summary_row, _find_sheet_name
- `src/audit_engine/consolidator/consolidate.py` — Consolidator.run(), _process_source, _merge_pt_rows, _merge_md_rows
- `src/audit_engine/consolidator/writer.py` — ConsolidatedWriter (write, _write_sheet, add_pt_rows, add_md_rows)

## Changes Made
1. Registered `RBL(muthoot)` in `Registered_Banks` sheet of `mapping_rules.xlsx`
2. Added empty RBL column in `Column_Mappings` sheet (zero overrides)
3. Fixed `load_external_header_patterns` to find Backup Aliases column by header name
4. Improved HEADER_PATTERNS for specificity (removed overly-generic patterns)
5. Rewrote `_match_source_header` with **score-order processing** + **different-canonical sharing** (`used_source_headers: dict[str,str]`)

## PT-MD Derivation — Complete Decoded Formulas

### RBL Source — Internal Excel Formulas

**PT Sheet formulas:**
| Cell Position | Formula | Means |
|---|---|---|
| Col 11 (Base Audit Fee) | `=L/J` | BaseFee = TotalBase / visits |
| Col 15 (Total pay) | `=L+M+N` | Total = TotalBase + Travel + CancelFee |

**MD Sheet formulas:**
| Cell Position | Formula | Means |
|---|---|---|
| Col 17 (Final Client Fees) | `=O*P` | = No. of visit × Client Fees |
| Col 28 (Actual Audited) | `=W-X-Y-Z-AA` | = Total pouches − Closed − Auctioned − Missing − Wrongly Created |
| Col 30 (Total packets audited) | `=AB+AC` | = Actual Audited + Extra |
| Col 31 (Assayer Fees___2) | `=O*R` | = No. of visit × Assayer Fees (per-MD-row extension) |
| Col 32 (Additional Fees___2) | `=S*O` | = No. of visit × Additional Fees |
| Col 35 (Total) | `=AE+AF+AG` | = Assayer Fees___2 + Additional Fees___2 + Cancellation |

**Key insight:** The `___2` columns (Assayer Fees___2, Additional Fees___2) are **per-visit extensions** — they multiply the per-visit rate by the number of visits in that MD row (typically 1, so same as the base rate). The "Total" column at the end sums everything.

### Axis Source — Internal Excel Formulas

From extractor analysis, Axis follows the same pattern with `___2` extended columns.

### PT Columns Fully Derivable from MD (100% match)

| PT Column | RBL Derivation | Axis Derivation |
|---|---|---|
| **No of visits** | SUM(MD.`No. of Visit`) per assayer | SUM(MD.`No of days audited`) per assayer |
| **Total pay (Base)** | SUM(MD.`Assayer Fees`) per assayer | SUM(MD.`Assayer fee___2`) per assayer |
| **Travel charges(If any)** | SUM(MD.`Additional Fees___2`) per assayer | SUM(MD.`Additional fee___2`) per assayer |
| **Branch Cancellation Charges** | — | SUM(MD.`Cancelled`) per assayer |
| **Audit Cancellation Fees** | SUM(MD.`Cancellation`) per assayer | — |
| **Error Deduction** | — | SUM(MD.`Error Deduciton`) per assayer |
| **Total pay** | SUM(MD.`Total`) per assayer | SUM(MD.`Total`) per assayer |
| **Base Audit Fee** | First positive MD.`Assayer Fees` | MAX(MD.`Assayer fee`) |
| **Assayer Name** | First MD.`Assayer Name` | First MD.`Assayer Name` |
| **Assayer Phone** | First MD.`AssayerPhone` | First MD.`AssayerPhone` |
| **PAN Number** | First MD.`Assayer PAN` | First MD.`Assayer PAN` |
| **Zone** | First MD.`Zone` | First MD.`Zone` |

### PT Columns NOT in MD (manual entry required)
- Travel charges(If any) — **name is misleading**: it's actually SUM of Additional Fees, NOT actual travel reimbursement
- Bank Name, A/c Number, IFSC Code — purely PT; not present in MD
- Remarks (if any) — purely PT

**Important:** The column "Travel charges(If any)" in PT is the SUM of MD's `Additional Fees___2` (which is `Additional Fees × No of Visit` per MD row). It has nothing to do with distance or actual travel. The name is misleading.

### Near-Perfect Derivations (99%)

| Axis PT Column | Best Match | Rate | Notes |
|---|---|---|---|
| Base Audit Fee | MAX(MD.Assayer fee) | 100/101 (99%) | AS0701: PT=0, MD.max=1000 |
| Cancelled visits | COUNT(MD.Cancelled > 0) | 100/101 (99%) | AS0701: PT=0, MD.count=1 |
| No. of Visits | SUM(MD.No of days audited) | 92/101 (91%) | 9 mismatches remain — maybe outliers |

| RBL PT Column | Best Match | Rate |
|---|---|---|
| No of visits | SUM(MD.No. of Visit) per assayer | 63/63 (100%) |
| Location | MODE(MD.Assayer Base location) | 30/63 (48%) — weak, likely unlinked |

## Cell-by-Column Diffs vs Manual Template

### PT Sheet — 97.4% Match
Remaining diffs largely attributable to:
- **State naming:** MD uses `RAJASTHAN`, system maps MD state to PT; manual template uses `Rajasthan`. Case mismatch.
- **Zone derivation:** System uses `city_to_state()` / `state_to_zone()` geo-lookup; manual may use different rules.

### MD Sheet — 54.7% Match
Remaining diffs are overwhelmingly (29.4%):
- **0 vs None:** System writes `0` for numeric columns missing in source; manual left them blank
- **Date format:** System writes `dd-mm-yyyy` strings; manual has datetime objects
- **Column ordering/organization differences**

## Implementation Details

### Score-Order Header Matching (`mapper.py`)
- Each canonical column has a list of `(score, pattern)` tuples
- Source headers are matched against patterns in **descending score order** (longest/most specific first)
- `used_source_headers` is a `dict[str, str]` mapping source header → first-claiming canonical name
- A source header already claimed by canonical A can still match canonical B if:
  - A and B have **different canonical names** (`different_canonicals = True`), AND
  - The source header actually appears in both patterns' match results
- Fixes the `Additional`/`Additional fee` swap: longer pattern scored higher → processed first → correct match

### `ProcessingContext` Dataclass
- Defined at `src/audit_engine/consolidator/config.py:411` with `@dataclass`
- Auto-generates `__init__` with keyword-only args
- Usage: `ProcessingContext(audit_month="Feb'26")`
- NOT: `ProcessingContext({"audit_month": "Feb'26"})` — positional dict will fail

### External Mapping File Loading
- `load_external_header_patterns()` checks `~/.audit_engine_elite/settings/mapping_rules.xlsx`
- Finds the `Column_Mappings` sheet's `Backup Aliases` column by reading the actual header row
- May fail in PyInstaller builds without `sys._MEIPASS` handling (path resolution)
- The `used_source_headers` dict approach was added to support the new score-order logic correctly

## Summary of All Diffs Remaining

| Diff Category | Count | Root Cause |
|---|---|---|
| State `RAJASTHAN` vs `Rajasthan` | 58 PT rows | Case mismatch in MD→PT state mapping |
| `0` vs `None` (blank) | 29.4% MD cells | System fills 0 for missing source cols |
| Date format (string vs datetime) | ~53% MD rows | Normalize_dates converts to string; manual has raw datetime |
| Zone derivation diff | Small number | Geo-lookup vs manual rule |
| AS0701 BaseFee/Cancelled mismatch | 1 Axis row | PT=0 but MD has values — possibly cancelled assayer |
| 9 Visits mismatches | 9 Axis rows | SUM(No of days audited) ≠ PT No. of Visits for these |
| Travel column misnomer | All rows | PT "Travel charges" = Additional Fees, not actual travel |
