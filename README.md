# IDFC Audit Engine Elite

Professional-grade PDF report generator for **IDFC FIRST Bank** gold-loan audits.

Reads Excel master files containing loan records (prospect numbers, CUIDs, tare weights, branch assignments), groups them by bank branch, and produces one **landscape A4 PDF** per branch — formatted as an audit worksheet ready for field auditors.

## Requirements

- **Python 3.9+**
- Dependencies (install via `pip install -r requirements.txt`):
  - `openpyxl` — Excel file parsing
  - `pandas` — Data handling
  - `reportlab` — PDF generation
  - `pyinstaller` — Standalone executable builds

## Quick Start

```bash
# 1. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch the GUI
python pdf_generator_ui.py
```

## Usage

1. **Select Excel File** — Click "SELECT FILE" and choose your audit master `.xlsx`
2. **Configure** — Set audit type (POA/TAF), output mode (Folder/ZIP/Both)
3. **Choose Output** — Set destination directory
4. **Generate** — Click "START GENERATION ENGINE"
5. **Review** — PDFs are organized in a timestamped subfolder

### Excel File Requirements

Your Excel file must contain a sheet with **all** of these columns (case-insensitive):

| Column | Description |
|--------|-------------|
| `Prospectno` | Prospect/loan number |
| `CUID` | Customer unique identifier |
| `Tare Weight` | Gold tare weight as per bank records |
| `State` | State/region |
| `CurrentBranch` | Branch code |
| `CurrentBranchName` | Branch name |

## Building Standalone Executable

### macOS / Linux
```bash
chmod +x BUILD_FOR_MAC_LINUX.sh
./BUILD_FOR_MAC_LINUX.sh
```

### Windows
```cmd
BUILD_FOR_WINDOWS.bat
```

The standalone executable will be created at `dist/IDFC_Audit_Engine_Elite`.

## Project Structure

```
pdf_generator/
├── pdf_generator_ui.py    # GUI application (Tkinter)
├── pdf_logic.py           # Core logic: Excel parsing, PDF generation
├── pdf_generator.spec     # PyInstaller build configuration
├── requirements.txt       # Python dependencies
├── fonts/                 # Bundled fonts (Carlito, Arimo)
├── tests/                 # Unit tests
├── BUILD_FOR_MAC_LINUX.sh # macOS/Linux build script
└── BUILD_FOR_WINDOWS.bat  # Windows build script
```

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

## Features

- **Data Preview** — Validates Excel and shows row/branch counts before generation
- **Cancel Support** — Stop a long-running batch mid-process
- **ZIP Packaging** — Output as folder, ZIP archive, or both
- **Analytics Dashboard** — Track audit type distribution and daily activity
- **Generation History** — Searchable log with export-to-Excel support
- **Persistent Settings** — Remembers output path, audit type, and preferences
- **File Logging** — Diagnostic logs saved to `~/.idfc_audit_engine.log`
- **Cross-Platform** — Works on Windows, macOS, and Linux
