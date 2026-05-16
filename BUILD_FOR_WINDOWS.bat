@echo off
setlocal enabledelayedexpansion

:: ========================================================
:: IDFC PDF GENERATOR - ULTIMATE BUILDER v4.3
:: ========================================================
:: Support for: Windows, Parallels (Mac), Network Drives
:: ========================================================

:: 1. DETECT UNC / NETWORK PATHS
set "ORIGINAL_DIR=%~dp0"
set "IS_UNC=0"
if "%ORIGINAL_DIR:~0,2%"=="\\" set "IS_UNC=1"

if "%IS_UNC%"=="1" (
    echo [!] UNC Path Detected: %ORIGINAL_DIR%
    echo [!] PyInstaller does not support network paths.
    echo [*] Creating a LOCAL SANDBOX for building...
    
    set "TEMP_BUILD_DIR=C:\IDFC_Build_Temp"
    if exist "!TEMP_BUILD_DIR!" rd /s /q "!TEMP_BUILD_DIR!"
    mkdir "!TEMP_BUILD_DIR!"
    
    echo [*] Copying files to local sandbox...
    xcopy /E /I /Y /Q "%ORIGINAL_DIR%*" "!TEMP_BUILD_DIR!\" >nul
    
    cd /d "!TEMP_BUILD_DIR!"
    echo [+] Switched to local workspace: !CD!
) else (
    pushd "%~dp0" >nul 2>&1
)

:: Verify directory stability
if /i "%CD%"=="C:\Windows" (
    echo [!!!] ERROR: Still in C:\Windows. Please run from a local folder.
    pause
    exit /b
)

echo ========================================================
echo [+] STARTING BUILD PROCESS...
echo ========================================================

:: 2. PYTHON CONFIGURATION
set "PY_CMD="
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=python"
) else (
    if exist "py_portable\python.exe" (
        set "PY_CMD=%CD%\py_portable\python.exe"
    ) else (
        echo [!] Downloading Portable Python...
        mkdir "py_portable" >nul 2>&1
        powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip', 'py_portable\py.zip')"
        powershell -Command "Expand-Archive -Path 'py_portable\py.zip' -DestinationPath 'py_portable' -Force"
        del "py_portable\py.zip"
        for %%f in (py_portable\*._pth) do (echo python311.zip> "%%f" & echo .>> "%%f" & echo import site>> "%%f")
        powershell -Command "(New-Object System.Net.WebClient).DownloadFile('https://bootstrap.pypa.io/get-pip.py', 'py_portable\get-pip.py')"
        .\py_portable\python.exe py_portable\get-pip.py --no-warn-script-location
        set "PY_CMD=%CD%\py_portable\python.exe"
    )
)

:: 3. DEPENDENCIES
echo [*] Syncing libraries...
"!PY_CMD!" -m pip install openpyxl pandas reportlab pyinstaller --no-warn-script-location --quiet

:: 4. THE BUILD
if exist "dist" rd /s /q "dist"
if exist "build" rd /s /q "build"
echo [*] Executing PyInstaller...
"!PY_CMD!" -m PyInstaller --noconfirm --clean pdf_generator.spec

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo [+++] BUILD SUCCESSFUL [+++]
    echo ========================================================
    
    if "%IS_UNC%"=="1" (
        echo [*] Moving EXE back to network folder...
        if exist "%ORIGINAL_DIR%dist" rd /s /q "%ORIGINAL_DIR%dist"
        mkdir "%ORIGINAL_DIR%dist"
        xcopy /Y /Q "dist\IDFC_Audit_Engine_Elite.exe" "%ORIGINAL_DIR%\" >nul
        echo [+] Single EXE ready at: %ORIGINAL_DIR%IDFC_Audit_Engine_Elite.exe
        
        echo [*] Cleaning up local sandbox...
        cd /d "%TEMP%\.."
        rd /s /q "!TEMP_BUILD_DIR!"
    ) else (
        echo [+] Single EXE ready at: %CD%\dist\IDFC_Audit_Engine_Elite.exe
    )
) else (
    echo [!!!] BUILD FAILED.
)

echo Build process finished. Window will close in 10s.
timeout /t 10
if "%IS_UNC%"=="0" popd
exit /b
