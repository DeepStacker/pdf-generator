#!/bin/bash

# ========================================================
# IDFC PDF GENERATOR - MAC/LINUX BUILDER v4.3
# ========================================================

echo "========================================================"
echo "[+] DETECTING SYSTEM..."
echo "========================================================"

# Detect OS
OS_TYPE="$(uname)"
echo "[*] OS: $OS_TYPE"

# 1. Check for Python
if command -v python3 &>/dev/null; then
    PY_CMD="python3"
elif command -v python &>/dev/null; then
    PY_CMD="python"
else
    echo "[!!!] Error: Python is not installed."
    echo "Please install Python 3.9+ from python.org or your package manager."
    exit 1
fi

echo "[*] Using Python: $($PY_CMD --version)"

# 2. Setup Virtual Environment (Portable logic)
if [ ! -d ".venv" ]; then
    echo "[*] Creating virtual environment..."
    $PY_CMD -m venv .venv
fi
source .venv/bin/activate

# 3. Install Dependencies
echo "[*] Installing requirements..."
pip install --upgrade pip --quiet
pip install openpyxl pandas reportlab pyinstaller --quiet

# 4. Build the App
echo "========================================================"
echo "[+] BUILDING APPLICATION..."
echo "========================================================"

# Remove old builds
rm -rf dist build

# Run PyInstaller
pyinstaller --noconfirm --clean pdf_generator.spec

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================================"
    echo "[+++] SUCCESS! [+++]"
    echo "Your standalone app is ready at: dist/IDFC_Audit_Engine_Elite"
    echo "========================================================"
else
    echo ""
    echo "[!!!] BUILD FAILED [!!!]"
fi
