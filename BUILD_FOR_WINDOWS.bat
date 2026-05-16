@echo off
setlocal enabledelayedexpansion

:: UNIVERSAL PATH HANDLING
pushd "%~dp0"

echo ========================================================
echo IDFC PDF GENERATOR - ULTIMATE WINDOWS BUILDER
echo ========================================================
echo.

:: 1. CHECK FOR SYSTEM-WIDE PYTHON
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_EXE=python"
    echo [+] Using System Python.
    goto :CHECK_TKINTER
)

:: 2. SETUP PORTABLE VERSION (FOR NO-ADMIN / RESTRICTED SYSTEMS)
if not exist "py_portable" mkdir "py_portable"
cd py_portable

if not exist "python.exe" (
    echo [!] No Python found. Setting up a private portable version...
    echo [*] Downloading components (requires internet)...
    
    :: NOTE: Embeddable Python does NOT have tkinter. 
    :: If user needs tkinter, we recommend manual installation.
    curl -L -o py.zip https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip
    tar -xf py.zip
    del py.zip
    
    for %%f in (*._pth) do (
        echo python311.zip> "%%f"
        echo .>> "%%f"
        echo import site>> "%%f"
    )
    
    curl -L -o get-pip.py https://bootstrap.pypa.io/get-pip.py
    .\python.exe get-pip.py --no-warn-script-location
)

set "PY_EXE=%CD%\python.exe"
cd ..

:CHECK_TKINTER
echo [*] Verifying Tkinter...
"!PY_EXE!" -c "import tkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] WARNING: Your Python installation does NOT have 'tkinter'.
    echo [!] This is required for the UI.
    echo [!] Please install Python from python.org and check "tcl/tk and IDLE" during setup.
    pause
    exit /b
)

:INSTALL_LIBS
echo.
echo [*] Installing required libraries...
"!PY_EXE!" -m pip install openpyxl pandas reportlab pyinstaller --no-warn-script-location --quiet

echo.
echo ========================================================
echo BUILDING THE FINAL EXE (WITH TKINTER FIX)
echo ========================================================
if exist "dist" rd /s /q "dist"
if exist "build" rd /s /q "build"

"!PY_EXE!" -m PyInstaller --clean --noconfirm pdf_generator.spec

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo [+] SUCCESS! 
    echo [+] Your Windows file is ready in:
    echo     dist\IDFC_PDF_Generator\IDFC_PDF_Generator.exe
    echo ========================================================
) else (
    echo.
    echo [!] ERROR: The build process failed.
)

pause
popd
