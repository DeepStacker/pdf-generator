# Audit Engine Elite

Multi-bank gold-loan audit report generator. Reads Excel master files, detects the bank (IDFC / Equitas / Arvog), groups by branch, and produces landscape A4 PDF audit worksheets — plus optional colour-coded Excel templates for field auditors.

- **Banks:** IDFC First Bank, Equitas SFB (Stage 1 & 2), Arvog Bank
- **Output:** PDF audit worksheets + colour-coded Excel templates
- **Distribution:** Cross-platform standalone binaries (Windows/macOS/Linux)
- **Auto-update:** Background version checker with preflight validation
- **CI/CD:** Fully automated build & release pipeline via GitHub Actions

## Quick Start

```bash
# 1. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows

# 2. Install
pip install -e ".[all]"

# 3. Launch GUI
audit-engine
```

## Project Structure

```
pdf_generator/
├── .githooks/
│   └── pre-commit                    # Auto-bump patch version on commit
├── .github/workflows/
│   ├── test.yml                      # CI: ruff lint + pytest (3.11/3.12/3.13)
│   └── build-binaries.yml            # Build + release on version bump
├── fonts/
│   ├── Carlito-Regular.ttf
│   └── Arimo-Bold.ttf
├── scripts/
│   ├── BUILD_FOR_MAC_LINUX.sh        # Manual PyInstaller build (macOS/Linux)
│   ├── BUILD_FOR_WINDOWS.bat         # Manual PyInstaller build (Windows)
│   ├── setup-hooks.sh                # Install git hooks (run once)
│   └── create_distribution_zip.py    # Source distribution ZIP
├── src/audit_engine/
│   ├── __main__.py                   # CLI entry point
│   ├── _version.py                   # Single source of truth for version
│   ├── app.py                        # Bottle WSGI app factory
│   ├── database/
│   │   ├── legacy.py                 # Legacy JSON-based DB
│   │   └── repos.py                  # SQLite-based repositories
│   ├── domain/
│   │   ├── enums.py                  # BankType, OutputMode, etc.
│   │   └── models.py                 # Dataclasses for requests/results
│   ├── lib/bottle.py                 # Vendored Bottle WSGI micro-framework
│   ├── services/
│   │   ├── base.py                   # Abstract BankService base class
│   │   ├── idfc.py                   # IDFC First Bank
│   │   ├── equitas.py                # Equitas SFB (Stage 1 + Stage 2)
│   │   └── arvog.py                  # Arvog Bank
│   ├── tasks/
│   │   ├── tracker.py                # Thread-safe progress tracker
│   │   └── workers.py                # Background worker threads
│   ├── ui/static/
│   │   ├── index.html
│   │   ├── app.js
│   │   └── style.css
│   ├── updater/client.py             # Auto-update client
│   ├── utils/
│   │   ├── config.py                 # Configuration helpers
│   │   ├── dialogs.py                # Native file dialogs
│   │   └── platform.py               # Platform detection
│   └── web/
│       ├── bridge.py                 # WebView ↔ Bottle bridge
│       ├── detect.py                 # Bank detection from Excel headers
│       ├── handlers.py               # Route handlers
│       ├── preprocess.py             # Excel column remapping
│       └── routes.py                 # Route registration
├── tests/                            # 250 tests across 19 test files
│   ├── conftest.py                   # Shared fixtures
│   └── test_*.py                     # Per-module test files
├── pyproject.toml                    # Project config, deps, tool settings
└── pdf_generator.spec                # PyInstaller spec file
```

## Hooks & Automatic Versioning

### One-time Setup

```bash
bash scripts/setup-hooks.sh
```

This runs `git config core.hooksPath .githooks`, activating the project's pre-commit hook.

### How It Works

**Pre-commit hook** (`.githooks/pre-commit`):
- Runs automatically on every `git commit`
- Bumps the patch version in `src/audit_engine/_version.py` (e.g. `5.2.217` → `5.2.218`)
- Stages the version file so the bump is included in your commit
- Skips if you already staged version changes manually

If you need to skip auto-bumping (e.g. WIP commits), stage `_version.py` yourself first — the hook will detect it and pass through.

## Automated Release Pipeline

### The Flow

```
git add .
git commit -m "fix: something"     # pre-commit hook bumps version
                          └── _version.py auto-bumped + staged
git push                 ──► CI kicks off:
                               1. test.yml: ruff lint + pytest (3.11/3.12/3.13)
                               2. build-binaries.yml (only if _version.py changed):
                                  a. setup: create tag vX.Y.Z + GitHub Release
                                  b. windows: PyInstaller → .zip + SHA256 → upload
                                  c. macos:   PyInstaller → .zip + SHA256 → upload
                                  d. linux:   PyInstaller → .tar.gz + SHA256 → upload
```

### What Gets Created

| Artifact | Platform | Format |
|---|---|---|
| Windows binary | Windows | `.zip` + `.sha256` |
| macOS app bundle | macOS | `.zip` + `.sha256` |
| Linux binary | Linux | `.tar.gz` + `.sha256` |

All assets are uploaded to a **GitHub Release** tagged `vX.Y.Z`, along with SHA-256 checksums for integrity verification.

### Manual Trigger

You can also trigger a build from GitHub UI: Actions → **Build & Release** → Run workflow.

### Workflows

| File | Trigger | Purpose |
|---|---|---|
| `.github/workflows/test.yml` | Push to `main`/`refactor/architecture`, PR to `main` | Lint + test across Python 3.11/3.12/3.13 |
| `.github/workflows/build-binaries.yml` | Push to `main` with `_version.py` changes, tag push `v*`, manual dispatch | Extract version → create tag → create release → build platform binaries → upload with checksums |

## Auto-Update Mechanism

The built-in updater (`src/audit_engine/updater/client.py`) handles all aspects of keeping binaries up to date:

### Background Checks
- Starts 15 seconds after app launch
- Polls GitHub Releases every hour
- Caches the latest release info for 1 hour
- Runs even in dev mode (logs but does not install)

### Preflight Validation
Before downloading, the updater validates:
- App is running as a frozen PyInstaller binary
- Existing executable exists and is accessible
- Install directory is writable
- At least 200 MB of free disk space
- Platform/architecture matches the release asset
- Network is reachable (HEAD request to release URL)

### Installation
- Extracts `.zip` (Windows/macOS) or `.tar.gz` (Linux) archives
- Replaces macOS `.app` bundles atomically
- Ad-hoc re-signs on macOS after replacement
- Falls back gracefully on errors

## Building Standalone

### From CI (Recommended)

Push to `main` with a version bump — see _Automated Release Pipeline_ above.

### Manual Build

```bash
# macOS / Linux
bash scripts/BUILD_FOR_MAC_LINUX.sh

# Windows
scripts\BUILD_FOR_WINDOWS.bat
```

Output is at `dist/Audit_Engine_Elite` (or `Audit_Engine_Elite.app` on macOS).

## Running Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v                # 250 tests
pytest tests/ -v -k "idfc"     # Run IDFC-specific tests only
```

## Linting & Formatting

```bash
ruff check src/ tests/          # Lint
ruff format src/ tests/         # Format
ruff check --fix src/ tests/    # Auto-fix
```

### Pre-commit Config (Optional)

The repo includes `.pre-commit-config.yaml` with ruff hooks. Install via:

```bash
pip install pre-commit
pre-commit install
```

## Configuration

The application database path defaults to `~/.idfc_pdf_generator_v3.db`. This is set in `src/audit_engine/utils/config.py`.

### Python Dependencies

| Dependency | Purpose |
|---|---|
| `bottle` | WSGI micro-framework (vendored) |
| `reportlab` | PDF generation |
| `openpyxl` | Excel file I/O |
| `numpy<2` | Numerical operations (pandas dependency) |
| `pandas<2.2` | Data manipulation |
| `certifi` | SSL certificate bundle for HTTPS requests |
| `sv-ttk` | Modern ttk theme for Tkinter |

## Version Scheme

Versions follow a `MAJOR.MINOR.PATCH` scheme:
- `__version__` in `src/audit_engine/_version.py` is the single source of truth
- `VERSION` and `APP_TITLE` are aliases for compatibility
- Patch is auto-incremented on every commit via pre-commit hook
- Tags (`vMAJOR.MINOR.PATCH`) are auto-created by CI on push to `main`
