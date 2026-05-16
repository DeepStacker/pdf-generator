@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo IDFC PDF GENERATOR - ULTIMATE WINDOWS BUILDER
echo ========================================================
echo.

:: 1. CHECK IF PYTHON IS ALREADY INSTALLED
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=python"
    goto :INSTALL_LIBS
)

:: 2. CHECK IF 'py' LAUNCHER IS INSTALLED
py --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=py"
    goto :INSTALL_LIBS
)

:: 3. IF NOT FOUND, INSTALL PYTHON AUTOMATICALLY
echo [!] Python was not detected on this system.
echo [*] I will now install Python 3.11 for you.
echo [*] Downloading...

set "INSTALLER=python_installer.exe"
curl -L -o "!INSTALLER!" https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe

echo [*] Installing... Please wait (this takes ~1 min)...
:: Install quietly, add to path, and install pip
start /wait "" "!INSTALLER!" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_pip=1

:: Try to find the newly installed python if path isn't refreshed
set "USER_PY=%LocalAppData%\Programs\Python\Python311\python.exe"
if exist "!USER_PY!" (
    set "PY_CMD=!USER_PY!"
) else (
    echo [!] Installation finished, but I cannot find python.exe.
    echo [!] Please RESTART your computer and run this script again.
    del "!INSTALLER!"
    pause
    exit /b
)

del "!INSTALLER!"
echo [+] Python installed successfully.

:INSTALL_LIBS
echo [*] Using: !PY_CMD!
echo [*] Updating pip...
"!PY_CMD!" -m pip install --upgrade pip --user --quiet

echo [*] Installing required libraries (this may take a moment)...
"!PY_CMD!" -m pip install openpyxl pandas reportlab pyinstaller --user --quiet

echo.
echo ========================================================
echo BUILDING THE EXE FILE
echo ========================================================
echo [*] Cleaning old builds...
if exist "dist" rd /s /q "dist"
if exist "build" rd /s /q "build"

echo [*] Running PyInstaller...
"!PY_CMD!" -m PyInstaller --clean --noconfirm --noconsole --add-data "fonts;fonts" --hidden-import tkinter --hidden-import openpyxl --hidden-import pandas pdf_generator_ui.py

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo [+] SUCCESS! 
    echo [+] Your Windows file is here:
    echo     dist\pdf_generator_ui\pdf_generator_ui.exe
    echo.
    echo You can rename 'pdf_generator_ui.exe' to 'IDFC_Generator.exe'
    echo ========================================================
) else (
    echo.
    echo [!] ERROR: The build failed. 
    echo [!] Please ensure you have an active internet connection.
    echo [!] If this continues, try installing Python manually from python.org
    pause
)

pause
