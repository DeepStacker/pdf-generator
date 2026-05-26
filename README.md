# Audit Engine Elite

Multi-bank gold-loan audit report generator. Reads Excel master files, detects the bank (IDFC / Equitas / Arvog), groups by branch, and produces landscape A4 PDF audit worksheets — plus optional colour-coded Excel templates for field auditors.

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
├── src/audit_engine/
│   ├── __main__.py        # Entry point
│   ├── app.py             # WSGI app factory
│   ├── services/          # Bank-specific PDF logic
│   │   ├── idfc.py        # IDFC First Bank
│   │   ├── equitas.py     # Equitas SFB (Stage 1 + Stage 2)
│   │   └── arvog.py       # Arvog Bank
│   ├── web/               # Bottle routes & handlers
│   ├── tasks/             # Background thread workers
│   ├── database/          # SQLite repos
│   ├── utils/             # Config, platform, dialogs
│   ├── updater/           # Auto-update client
│   ├── domain/            # Enums & models
│   └── lib/bottle.py      # Vendored Bottle WSGI
├── tests/                 # Test suite (73 tests)
├── fonts/                 # Bundled fonts (Carlito, Arimo)
├── scripts/               # Build & release scripts
├── pyproject.toml         # Project config & deps
└── pdf_generator.spec     # PyInstaller spec
```

## Building Standalone

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
pytest tests/ -v
```

## Linting

```bash
ruff check src/ tests/
ruff format src/ tests/
```
