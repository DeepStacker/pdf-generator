@echo off
setlocal enabledelayedexpansion

:: UNIVERSAL PATH HANDLING
:: Works on Network Shares (UNC), Shared Mac Folders, and Local Drives
pushd "%~dp0"

echo ========================================================
echo IDFC PDF GENERATOR - UNIVERSAL WINDOWS BUILDER
echo ========================================================
echo.

:: 1. CHECK FOR SYSTEM-WIDE PYTHON
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_EXE=python"
    echo [+] Using System Python.
    goto :INSTALL_LIBS
)

:: 2. SETUP PORTABLE VERSION (FOR NO-ADMIN / RESTRICTED SYSTEMS)
if not exist "py_portable" mkdir "py_portable"
cd py_portable

if not exist "python.exe" (
    echo [!] No Python found. Setting up a private portable version...
    echo [*] Downloading components (requires internet)...
    
    :: Download Python 3.11 Embeddable
    curl -L -o py.zip https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip
    if %errorlevel% neq 0 ( echo [!] Download failed. Check internet. & pause & exit /b )
    
    echo [*] Extracting...
    tar -xf py.zip
    del py.zip
    
    echo [*] Configuring environment...
    :: Dynamically find and fix the .pth file to enable libraries
    for %%f in (*._pth) do (
        echo [DEBUG] Configuring %%f
        echo python311.zip> "%%f"
        echo .>> "%%f"
        echo import site>> "%%f"
    )
    
    echo [*] Installing Pip...
    curl -L -o get-pip.py https://bootstrap.pypa.io/get-pip.py
    .\python.exe get-pip.py --no-warn-script-location
)

set "PY_EXE=%CD%\python.exe"
cd ..

:INSTALL_LIBS
echo.
echo [*] Installing required libraries...
"!PY_EXE!" -m pip install openpyxl pandas reportlab pyinstaller --no-warn-script-location --quiet

echo.
echo ========================================================
echo BUILDING THE FINAL EXE
echo ========================================================
if exist "dist" rd /s /q "dist"
if exist "build" rd /s /q "build"

"!PY_EXE!" -m PyInstaller --clean --noconfirm --noconsole --add-data "fonts;fonts" --hidden-import tkinter --hidden-import openpyxl --hidden-import pandas pdf_generator_ui.py

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo [+] SUCCESS! 
    echo [+] Your Windows file is ready in:
    echo     dist\pdf_generator_ui\pdf_generator_ui.exe
    echo.
    echo [+] You can now send that .exe to anyone.
    echo ========================================================
) else (
    echo.
    echo [!] ERROR: The build process failed.
)

pause
popd
