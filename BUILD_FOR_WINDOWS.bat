@echo off
setlocal enabledelayedexpansion

:: ========================================================
:: IDFC AUDIT ENGINE ELITE - WINDOWS PORTABLE BUILDER v5.0.1
:: ========================================================
:: Support for: Windows 10/11, Parallels (Mac), Network Drives (UNC)
:: Design: Fully automated, flat control flow branching to prevent cmd parser crashes.

title IDFC Audit Engine Elite - Builder
echo ========================================================
echo [+] STARTING BUILD PROCESS...
echo ========================================================

:: 1. DETECT UNC / NETWORK PATHS
set "ORIGINAL_DIR=%~dp0"
set "IS_UNC=0"
if "%ORIGINAL_DIR:~0,2%"=="\\" set "IS_UNC=1"

if "%IS_UNC%"=="1" (
    echo [!] UNC Network Path Detected: %ORIGINAL_DIR%
    echo [*] PyInstaller does not support network builds directly.
    echo [*] Creating a LOCAL SANDBOX for compiling...
    
    set "TEMP_BUILD_DIR=C:\IDFC_Build_Sandbox"
    if exist "!TEMP_BUILD_DIR!" rd /s /q "!TEMP_BUILD_DIR!"
    mkdir "!TEMP_BUILD_DIR!"
    
    echo [*] Copying project files to local sandbox...
    xcopy /E /I /Y /Q "%ORIGINAL_DIR%*" "!TEMP_BUILD_DIR!\" >nul
    
    cd /d "!TEMP_BUILD_DIR!"
    echo [+] Switched to local workspace: !CD!
) else (
    pushd "%~dp0" >nul 2>&1
)

:: Verify directory stability
if /i "%CD%"=="C:\Windows" (
    echo [!!!] ERROR: Active directory is C:\Windows. Running here is unsafe.
    echo Please move the project to a local folder like C:\Users\Public or Desktop.
    pause
    exit /b 1
)

:: 2. DETECT AND VALIDATE PYTHON (WITH TKINTER)
echo [*] Searching for compatible Python installation...
set "PY_CMD="

:: Check standard command 'python'
python --version >nul 2>&1
if %errorlevel% neq 0 goto CHECK_PY_LAUNCHER
python -c "import tkinter" >nul 2>&1
if %errorlevel% neq 0 goto CHECK_PY_LAUNCHER
set "PY_CMD=python"
echo [+] Found working system Python with Tkinter.
goto STEP_4

:CHECK_PY_LAUNCHER
:: Check 'py' launcher
py --version >nul 2>&1
if %errorlevel% neq 0 goto INSTALL_PYTHON_WINGET
py -c "import tkinter" >nul 2>&1
if %errorlevel% neq 0 goto INSTALL_PYTHON_WINGET
set "PY_CMD=py"
echo [+] Found working Python launcher (py) with Tkinter.
goto STEP_4

:INSTALL_PYTHON_WINGET
echo [!] Compatible Python with Tkinter was NOT found on this system.
echo [*] Launching automated Python installation...

:: Try Winget first (modern Windows 10/11)
where winget >nul 2>&1
if %errorlevel% neq 0 goto INSTALL_PYTHON_WEB
echo [*] Installing official Python via Winget (Silent)...
winget install --id Python.Python.3.11 --silent --accept-source-agreements --accept-package-agreements >nul 2>&1

:: Wait and search in local AppData
set "WINGET_PY_PATH=%LocalAppData%\Programs\Python\Python311\python.exe"
if exist "!WINGET_PY_PATH!" (
    set "PY_CMD=!WINGET_PY_PATH!"
    echo [+] Python 3.11 successfully installed via Winget.
    goto STEP_4
)

:INSTALL_PYTHON_WEB
:: Try WebClient + Silent Installer if Winget failed/missing
echo [*] Downloading official Python 3.11 Installer...
set "INSTALLER_EXE=%TEMP%\python_311_installer.exe"

powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe', '%TEMP%\python_311_installer.exe')"

if not exist "%TEMP%\python_311_installer.exe" goto INSTALL_PORTABLE_PYTHON
echo [*] Installing Python 3.11 silently (No admin rights required)...
start /wait "" "%TEMP%\python_311_installer.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_pip=1 AssociateFiles=0 Shortcuts=0
del "%TEMP%\python_311_installer.exe"

:: Search in user profiles
set "USER_PY_PATH=%LocalAppData%\Programs\Python\Python311\python.exe"
if exist "!USER_PY_PATH!" (
    set "PY_CMD=!USER_PY_PATH!"
    echo [+] Python 3.11 successfully installed via web installer.
    goto STEP_4
)

:INSTALL_PORTABLE_PYTHON
:: Absolute desperate fallback: Embeddable Python (Might lack Tkinter UI binding at runtime)
if exist "py_portable\python.exe" (
    set "PY_CMD=%CD%\py_portable\python.exe"
    echo [!] WARNING: Falling back to pre-existing portable Python. GUI might not render.
    goto STEP_4
)

echo [!] WARNING: All full Python installers failed or were unavailable.
echo [*] Attempting desperate fallback to portable embeddable zip...
mkdir "py_portable" >nul 2>&1
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip', 'py_portable\py.zip')"
powershell -Command "Expand-Archive -Path 'py_portable\py.zip' -DestinationPath 'py_portable' -Force"
del "py_portable\py.zip"

for %%f in (py_portable\*._pth) do (
    echo python311.zip> "%%f"
    echo .>> "%%f"
    echo import site>> "%%f"
)

powershell -Command "(New-Object System.Net.WebClient).DownloadFile('https://bootstrap.pypa.io/get-pip.py', 'py_portable\get-pip.py')"
.\py_portable\python.exe py_portable\get-pip.py --no-warn-script-location
set "PY_CMD=%CD%\py_portable\python.exe"
echo [!] Embeddable Python configured as absolute fallback.

:STEP_4
:: 4. ENSURE PIP IS INSTALLED AND RUNNING
echo [*] Bootstrapping packages using: "!PY_CMD!"
"!PY_CMD!" -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Pip module is missing. Re-bootstrapping...
    "!PY_CMD!" -m ensurepip --default-pip >nul 2>&1
)

:: 5. INSTALL LIBRARIES
echo [*] Syncing required libraries (openpyxl, pandas, reportlab, pyinstaller)...
"!PY_CMD!" -m pip install openpyxl pandas reportlab pyinstaller --no-warn-script-location --quiet
if %errorlevel% neq 0 (
    echo [!] Standard installation had warnings. Retrying with --user...
    "!PY_CMD!" -m pip install openpyxl pandas reportlab pyinstaller --no-warn-script-location --user --quiet
)

:: 6. EXECUTE PYINSTALLER BUILD
if exist "dist" rd /s /q "dist"
if exist "build" rd /s /q "build"

echo ========================================================
echo [+] COMPILING SINGLE-FILE EXECUTIVE WITH PYINSTALLER...
echo ========================================================
"!PY_CMD!" -m PyInstaller --noconfirm --clean pdf_generator.spec

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo [+++] SUCCESS: BUILD COMPLETED SUCCESSFULLY! [+++]
    echo ========================================================
    
    if "%IS_UNC%"=="1" (
        echo [*] Transferring standalone EXE back to network path...
        if exist "%ORIGINAL_DIR%dist" rd /s /q "%ORIGINAL_DIR%dist"
        mkdir "%ORIGINAL_DIR%dist"
        copy /Y "dist\Audit_Engine_Elite.exe" "%ORIGINAL_DIR%dist\" >nul
        
        echo [+] Single EXE ready at: %ORIGINAL_DIR%dist\Audit_Engine_Elite.exe
        
        echo [*] Cleaning up local sandbox...
        cd /d "%TEMP%"
        rd /s /q "!TEMP_BUILD_DIR!"
    ) else (
        echo [+] Single EXE ready at: %CD%\dist\Audit_Engine_Elite.exe
    )
) else (
    echo.
    echo [!!!] COMPILATION ERROR: PyInstaller compilation failed.
    echo Please review the build log output above.
)

echo.
echo The builder has completed execution. Closing in 10 seconds.
timeout /t 10 >nul 2>&1 || ping -n 11 127.0.0.1 >nul
if "%IS_UNC%"=="0" popd
exit /b %errorlevel%
