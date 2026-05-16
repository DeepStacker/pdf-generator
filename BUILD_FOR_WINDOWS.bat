@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo IDFC PDF GENERATOR - WINDOWS BUILDER
echo ========================================================
echo This script will create the .exe file for you.
echo.

:: 1. Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found. Downloading a portable version...
    echo Please wait, this may take a minute...
    
    :: Create a temp folder for portable python
    if not exist "py_temp" mkdir "py_temp"
    
    :: Download portable python (3.11 for stability)
    curl -L -o py_temp\python_portable.zip https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip
    
    :: Note: Unzipping in a .bat without external tools is hard on older Windows, 
    :: but Windows 10+ has 'tar'
    tar -xf py_temp\python_portable.zip -C py_temp
    
    :: Download pip for the portable version
    curl -L -o py_temp\get-pip.py https://bootstrap.pypa.io/get-pip.py
    .\py_temp\python.exe py_temp\get-pip.py --no-warn-script-location
    
    set PYTHON_EXE=.\py_temp\python.exe
    echo Portable Python ready.
) else (
    set PYTHON_EXE=python
    echo Existing Python found.
)

echo.
echo Installing required libraries...
%PYTHON_EXE% -m pip install openpyxl pandas reportlab pyinstaller --quiet

echo.
echo Building the .exe file...
echo This will take about 1-2 minutes.
%PYTHON_EXE% -m PyInstaller --clean --noconfirm pdf_generator.spec

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo SUCCESS! 
    echo Your Windows file is here:
    echo dist\IDFC_PDF_Generator\IDFC_PDF_Generator.exe
    echo.
    echo You can now send that .exe to anyone!
    echo ========================================================
) else (
    echo.
    echo ERROR: Something went wrong during the build.
    pause
)

:: Cleanup temp files if they exist
:: if exist "py_temp" rd /s /q "py_temp"

pause
