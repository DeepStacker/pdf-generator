@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo IDFC PDF GENERATOR - NO-ADMIN WINDOWS BUILDER
echo ========================================================
echo.

:: 1. CHECK IF PYTHON IS ALREADY INSTALLED (SYSTEM WIDE)
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_EXE=python"
    goto :INSTALL_LIBS
)

:: 2. IF NO PYTHON, SETUP PORTABLE VERSION (NO ADMIN NEEDED)
echo [!] No Python found. Setting up a private portable version...
echo [*] This does NOT require admin password or installation.
echo.

if not exist "py_portable" mkdir "py_portable"
cd py_portable

if not exist "python.exe" (
    echo [*] Downloading Portable Python...
    curl -L -o python_zip.zip https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip
    
    echo [*] Extracting...
    tar -xf python_zip.zip
    del python_zip.zip
    
    echo [*] Enabling libraries...
    :: This is the CRITICAL fix for portable python: enable 'import site'
    for %%f in (python311._pth) do (
        echo python311.zip> "%%f"
        echo .>> "%%f"
        echo import site>> "%%f"
    )
    
    echo [*] Setting up pip...
    curl -L -o get-pip.py https://bootstrap.pypa.io/get-pip.py
    python.exe get-pip.py --no-warn-script-location
)

set "PY_EXE=%CD%\python.exe"
cd ..

:INSTALL_LIBS
echo [*] Using Python: "!PY_EXE!"
echo [*] Installing required libraries...
"!PY_EXE!" -m pip install openpyxl pandas reportlab pyinstaller --no-warn-script-location --quiet

echo.
echo ========================================================
echo BUILDING THE EXE FILE
echo ========================================================
if exist "dist" rd /s /q "dist"
if exist "build" rd /s /q "build"

"!PY_EXE!" -m PyInstaller --clean --noconfirm --noconsole --add-data "fonts;fonts" --hidden-import tkinter --hidden-import openpyxl --hidden-import pandas pdf_generator_ui.py

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo [+] SUCCESS! 
    echo [+] Your Windows file is here:
    echo     dist\pdf_generator_ui\pdf_generator_ui.exe
    echo ========================================================
) else (
    echo.
    echo [!] ERROR: The build failed. 
    pause
)

pause
