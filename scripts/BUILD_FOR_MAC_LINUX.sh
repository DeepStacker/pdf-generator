#!/bin/bash

# ========================================================
# IDFC AUDIT ENGINE ELITE - MAC/LINUX PORTABLE BUILDER v5.0.1
# ========================================================
# Design Philosophy: Adapt dynamically to any environment,
# diagnose issues clearly, and build a single-file executable.
# Automatically prioritizes Python runtimes with Tkinter support.

# Navigate to project root (one level up from scripts/)
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.."

# Colors for professional output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Parse arguments
FORCE_BUILD=false
for arg in "$@"; do
    if [ "$arg" = "--yes" ] || [ "$arg" = "-y" ]; then
        FORCE_BUILD=true
    fi
done

echo -e "${BLUE}========================================================${NC}"
echo -e "${BLUE}[+] IDFC AUDIT ENGINE ELITE - MAC/LINUX PORTABLE BUILDER${NC}"
echo -e "${BLUE}========================================================${NC}"

# Detect OS
OS_TYPE="$(uname)"
echo -e "[*] System OS: ${GREEN}$OS_TYPE${NC}"

# 1. Search for a Python 3 executable that has Tkinter support
echo -e "[*] Searching for a Python 3 installation with Tkinter support..."
PY_CMD=""
PY_VERSION=""

# Find all python3 and python executables in PATH, plus common system locations
ALL_PYTHONS=$(which -a python3 python 2>/dev/null)
# Also append common absolute paths just in case they're not in PATH
ALL_PYTHONS="$ALL_PYTHONS /usr/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3"

# Remove duplicate paths and check each one
UNIQUE_PYTHONS=$(echo "$ALL_PYTHONS" | tr ' ' '\n' | sort -u)

# First pass: Look for a Python 3 that HAS Tkinter
for py in $UNIQUE_PYTHONS; do
    if [ -x "$py" ]; then
        # Verify it's Python 3
        VER=$("$py" -c 'import sys; print(sys.version_info[0])' 2>/dev/null)
        if [ "$VER" = "3" ]; then
            # Test Tkinter
            if "$py" -c "import tkinter" &>/dev/null; then
                PY_CMD="$py"
                PY_VERSION=$("$py" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')
                echo -e "[+] Found Python with Tkinter: ${GREEN}$PY_CMD${NC} (version $PY_VERSION)"
                break
            fi
        fi
    fi
done

# Second pass fallback: If none have Tkinter, just find any Python 3
if [ -z "$PY_CMD" ]; then
    echo -e "${YELLOW}[!] No Python 3 with Tkinter found. Searching for any Python 3...${NC}"
    for py in $UNIQUE_PYTHONS; do
        if [ -x "$py" ]; then
            VER=$("$py" -c 'import sys; print(sys.version_info[0])' 2>/dev/null)
            if [ "$VER" = "3" ]; then
                PY_CMD="$py"
                PY_VERSION=$("$py" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')
                echo -e "[!] Selected Python without Tkinter: ${YELLOW}$PY_CMD${NC} (version $PY_VERSION)"
                break
            fi
        fi
    done
fi

if [ -z "$PY_CMD" ]; then
    echo -e "${RED}[!!!] ERROR: Python 3 is not installed or not in PATH.${NC}"
    echo -e "Please install Python 3.9+ from https://www.python.org/ or your package manager."
    exit 1
fi

# 2. Check for Tkinter (Critical for GUI)
echo -e "[*] Running final Tkinter check..."
if ! $PY_CMD -c "import tkinter" &>/dev/null; then
    echo -e "${YELLOW}[!] WARNING: 'tkinter' library is not available in $PY_CMD.${NC}"
    echo -e "The application requires Tkinter to render the GUI."
    echo ""
    if [ "$OS_TYPE" = "Darwin" ]; then
        echo -e "Suggested Fix for macOS:"
        echo -e "  - If using Homebrew: run ${BLUE}brew install python-tk${NC}"
        echo -e "  - Or download & install the official installer from ${BLUE}https://www.python.org/downloads/${NC} (recommended)"
    else
        echo -e "Suggested Fix for Linux:"
        echo -e "  - Debian/Ubuntu: run ${BLUE}sudo apt-get install python3-tk${NC}"
        echo -e "  - Fedora/RHEL: run ${BLUE}sudo dnf install python3-tkinter${NC}"
        echo -e "  - Arch Linux: run ${BLUE}sudo pacman -S tk${NC}"
    fi
    echo ""
    
    # Check if stdin is a terminal/TTY, or if we have force build flag
    if [ -t 0 ] && [ "$FORCE_BUILD" = "false" ]; then
        read -p "Do you want to attempt building anyway? (y/n) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${RED}[*] Build aborted by user due to missing Tkinter.${NC}"
            exit 1
        fi
    else
        echo -e "${YELLOW}[!] Non-interactive shell or --yes flag detected. Proceeding with compilation...${NC}"
    fi
else
    echo -e "[*] Tkinter check: ${GREEN}OK${NC}"
fi

# 3. Create or Activate Virtual Environment
VENV_ACTIVE=false

# We use a venv suffix based on Python version to avoid sharing caches between homebrew and system python
VENV_NAME=".venv_$(echo "$PY_VERSION" | cut -d. -f1,2 | tr . _)"

if [ -d "$VENV_NAME" ]; then
    echo -e "[*] Existing virtual environment '$VENV_NAME' found. Activating..."
    source "$VENV_NAME/bin/activate" && VENV_ACTIVE=true
else
    echo -e "[*] Creating fresh virtual environment '$VENV_NAME'..."
    if $PY_CMD -m venv "$VENV_NAME" &>/dev/null; then
        source "$VENV_NAME/bin/activate" && VENV_ACTIVE=true
        echo -e "[*] Virtual environment: ${GREEN}Created and Activated${NC}"
    else
        echo -e "${YELLOW}[!] WARNING: Could not create venv using 'venv' module (likely missing ensurepip or python3-venv).${NC}"
        echo -e "[*] Attempting fallback using 'virtualenv'..."
        if command -v virtualenv &>/dev/null; then
            virtualenv "$VENV_NAME" &>/dev/null && source "$VENV_NAME/bin/activate" && VENV_ACTIVE=true
            echo -e "[*] Virtual environment: ${GREEN}Created via virtualenv and Activated${NC}"
        else
            echo -e "${YELLOW}[!] WARNING: 'virtualenv' package not found. Proceeding with global user package installation...${NC}"
        fi
    fi
fi

# Determine pip command to run
PIP_CMD="python -m pip"
if [ "$VENV_ACTIVE" = "false" ]; then
    echo -e "${YELLOW}[*] Operating outside venv. Installing packages with '--user' for safety.${NC}"
    PIP_INSTALL="$PY_CMD -m pip install --user"
else
    PIP_INSTALL="python -m pip install"
fi

# 4. Install & Upgrade Dependencies
echo -e "[*] Upgrading pip..."
$PIP_INSTALL --upgrade pip --quiet 2>/dev/null || echo -e "${YELLOW}[!] Non-critical: Pip upgrade skipped.${NC}"

# Determine dependencies list (Linux needs pygobject for PyWebView GTK3/WebKit2 support)
DEPS="openpyxl pandas reportlab pyinstaller pywebview"
if [ "$OS_TYPE" != "Darwin" ]; then
    DEPS="$DEPS pygobject staticx"
    # Check and suggest system dependencies for Linux
    if command -v apt-get &>/dev/null; then
        MISSING_SYS=""
        for pkg in patchelf libgirepository-2.0-dev libcairo2-dev pkg-config gobject-introspection libgtk-3-dev libgdk-pixbuf-2.0-dev libwebkit2gtk-4.1-dev gir1.2-gtk-3.0 gir1.2-webkit2-4.1 gir1.2-girepository-3.0 gir1.2-soup-3.0; do
            if ! dpkg -s "$pkg" &>/dev/null; then
                MISSING_SYS="$MISSING_SYS $pkg"
            fi
        done
        if [ -n "$MISSING_SYS" ]; then
            echo -e "${YELLOW}[!] Missing system packages:$MISSING_SYS${NC}"
            echo -e "[*] Install them with: ${BLUE}sudo apt-get install$MISSING_SYS${NC}"
            if [ -t 0 ] && [ "$FORCE_BUILD" = "false" ]; then
                read -p "Attempt to install with sudo? (y/n) " -n 1 -r
                echo ""
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    sudo apt-get update && sudo apt-get install -y $MISSING_SYS || {
                        echo -e "${RED}[!] Failed to install system packages${NC}"
                        exit 1
                    }
                fi
            fi
        fi
    fi
fi

echo -e "[*] Installing required libraries ($DEPS)..."
if $PIP_INSTALL $DEPS --quiet; then
    echo -e "[*] Libraries installation: ${GREEN}SUCCESS${NC}"
else
    echo -e "${RED}[!!!] ERROR: Failed to install dependencies. Please check network connection and try again.${NC}"
    exit 1
fi

# 5. Build Standalone Application
echo -e "${BLUE}========================================================${NC}"
echo -e "${BLUE}[+] COMPILING STANDALONE ONE-FILE BINARY...${NC}"
echo -e "${BLUE}========================================================${NC}"

# Clean old artifacts
echo -e "[*] Cleaning old build files..."
rm -rf dist build

# Pre-query GI modules so PyInstaller's GI hooks find the typelibs
if [ "$OS_TYPE" != "Darwin" ]; then
    echo -e "[*] Pre-querying GI modules for PyInstaller cache..."
    export GI_TYPELIB_PATH="/usr/lib/x86_64-linux-gnu/girepository-1.0"
    python3 -c "
import gi
gi.require_version('GIRepository', '3.0'); from gi.repository import GIRepository
gi.require_version('Gtk', '3.0'); from gi.repository import Gtk, Gdk, GLib, Gio
gi.require_version('WebKit2', '4.1'); from gi.repository import WebKit2
gi.require_version('Soup', '3.0'); from gi.repository import Soup
print('GI modules OK')
" || echo -e "${YELLOW}[!] GI pre-query had warnings (non-fatal)${NC}"
    # Generate GTK runtime caches
    echo -e "[*] Generating GdkPixbuf loaders cache..."
    gdk-pixbuf-query-loaders /usr/lib/x86_64-linux-gnu/gdk-pixbuf-2.0/2.10.0/loaders/*.so \
        > gdk-pixbuf-loaders.cache 2>/dev/null
    sed -i 's|/usr/lib/x86_64-linux-gnu/gdk-pixbuf-2.0/2.10.0/loaders/|@MEIPASS@/gdk-pixbuf-loaders/|g' \
        gdk-pixbuf-loaders.cache 2>/dev/null
    echo -e "[*] Generating GTK immodules cache..."
    gtk-query-immodules-3.0 > gtk-immodules.cache 2>/dev/null
    sed -i 's|/usr/lib/x86_64-linux-gnu/gtk-3.0/3.0.0/immodules/|@MEIPASS@/gtk-immodules/|g' \
        gtk-immodules.cache 2>/dev/null
    echo -e "[*] Compiling GLib schemas..."
    sudo glib-compile-schemas /usr/share/glib-2.0/schemas/ 2>/dev/null || \
        glib-compile-schemas /usr/share/glib-2.0/schemas/ 2>/dev/null || true
fi

# Run PyInstaller via the python module interface for maximum platform compatibility
echo -e "[*] Invoking PyInstaller spec..."
if python -m PyInstaller --noconfirm --clean pdf_generator.spec; then
    echo ""
    echo -e "${BLUE}========================================================${NC}"
    echo -e "${GREEN}[+++] BUILD COMPLETED SUCCESSFULLY! [+++]${NC}"
    echo -e "${BLUE}========================================================${NC}"
    
    # Post-process with StaticX on Linux to bundle all shared library dependencies
    if [ "$OS_TYPE" != "Darwin" ] && [ -f "dist/Audit_Engine_Elite" ]; then
        echo -e "[*] Bundling all shared library dependencies with StaticX..."
        if command -v staticx &>/dev/null; then
            staticx dist/Audit_Engine_Elite dist/Audit_Engine_Elite
            echo -e "[+] StaticX: ${GREEN}DONE${NC}"
        else
            echo -e "${YELLOW}[!] staticx not found, skipping shared library bundling.${NC}"
            echo -e "${YELLOW}[!] The binary may not run on systems without GTK/WebKit2 installed.${NC}"
        fi
    fi
    
    # Locate output
    OUT_FILE=""
    if [ -f "dist/Audit_Engine_Elite" ]; then
        OUT_FILE="dist/Audit_Engine_Elite"
    elif [ -d "dist/Audit_Engine_Elite.app" ]; then
        OUT_FILE="dist/Audit_Engine_Elite.app"
    fi
    
    if [ -n "$OUT_FILE" ]; then
        FILE_SIZE=$(du -sh "$OUT_FILE" | cut -f1)
        echo -e "[+] Target Binary: ${GREEN}$OUT_FILE${NC}"
        echo -e "[+] Size: ${GREEN}$FILE_SIZE${NC}"
        echo -e "[+] Launch command: ${BLUE}./$OUT_FILE${NC}"
    else
        echo -e "${YELLOW}[!] Build succeeded but could not auto-locate output binary inside 'dist/'. Please inspect 'dist/' manually.${NC}"
    fi
    echo -e "${BLUE}========================================================${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}[!!!] BUILD COMPILATION FAILED [!!!]${NC}"
    echo -e "Please inspect the error logs above."
    exit 1
fi
