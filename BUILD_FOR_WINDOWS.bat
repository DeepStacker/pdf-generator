@echo off
setlocal enabledelayedexpansion

:: ========================================================
:: IDFC PDF GENERATOR - ENTERPRISE BUILDER v4.1
:: ========================================================
:: Designed for restricted, no-admin Windows environments.
:: ========================================================

:: 1. HANDLE UNC / NETWORK PATHS
:: If running from \\server\path, CMD will default to C:\Windows
:: We must use pushd to map a drive letter temporarily.
pushd "%~dp0" >nul 2>&1
if "%CD%"=="C:\Windows" (
    echo [!] WARNING: Running from a restricted system path or network drive.
    echo [!] Attempting to stabilize directory...
)

:: 2. PREVENT MULTIPLE INSTANCES (The "Hacker" Window Bug)
set "LOCK_FILE=%TEMP%\idfc_builder_lock.tmp"
if exist "%LOCK_FILE%" (
    :: Check if the lock file is old (older than 1 minute)
    :: For simplicity, we just warn and ask to continue if lock exists
    echo [!] Another instance of the builder might be running.
    echo [!] If you see many windows, please close them and delete:
    echo     %LOCK_FILE%
    set /p "cont=Continue anyway? (y/n): "
    if /i "!cont!" neq "y" exit /b
)
echo %DATE% %TIME% > "%LOCK_FILE%"

echo ========================================================
:: Header
echo [+] STARTING BUILD PROCESS...
echo ========================================================

:: 3. FIND PYTHON
set "PY_CMD="
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=python"
    echo [+] System Python detected.
) else (
    py --version >nul 2>&1
    if !errorlevel! equ 0 (
        set "PY_CMD=py"
        echo [+] Python Launcher detected.
    )
)

if "!PY_CMD!"=="" (
    echo [!] No System Python found. Using Portable Mode...
    if not exist "py_portable" mkdir "py_portable"
    cd py_portable
    if not exist "python.exe" (
        echo [*] Downloading Portable Python (3.11)...
        powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip', 'py.zip')"
        echo [*] Extracting...
        tar -xf py.zip
        del py.zip
        
        :: Enable site-packages for embeddable python
        for %%f in (*._pth) do (
            echo python311.zip> "%%f"
            echo .>> "%%f"
            echo import site>> "%%f"
        )
        
        echo [*] Installing Pip...
        powershell -Command "(New-Object System.Net.WebClient).DownloadFile('https://bootstrap.pypa.io/get-pip.py', 'get-pip.py')"
        .\python.exe get-pip.py --no-warn-script-location
        del get-pip.py
    )
    set "PY_CMD=%CD%\python.exe"
    cd ..
)

:: 4. VERIFY LIBRARIES
echo [*] Checking dependencies...
"!PY_CMD!" -m pip install openpyxl pandas reportlab pyinstaller --no-warn-script-location --quiet

:: 5. THE BUILD
echo.
echo ========================================================
echo BUILDING EXE... PLEASE WAIT (This may take 1-2 minutes)
echo ========================================================
if exist "dist" rd /s /q "dist"
if exist "build" rd /s /q "build"

"!PY_CMD!" -m PyInstaller --noconfirm --clean pdf_generator.spec

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo [+++] SUCCESS! [+++]
    echo.
    echo Location: dist\IDFC_PDF_Generator\IDFC_PDF_Generator.exe
    echo ========================================================
) else (
    echo.
    echo [!!!] BUILD FAILED [!!!]
    echo Check the error messages above.
)

:: CLEANUP
if exist "%LOCK_FILE%" del "%LOCK_FILE%"
echo.
echo Press any key to exit...
pause >nul
popd
exit /b
