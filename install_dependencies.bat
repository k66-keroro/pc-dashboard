@echo off
setlocal

echo =================================================================
echo  PC-Dashboard Dependency Installation Script
echo =================================================================
echo.
echo This script will help you set up the Python environment.
echo.
echo IMPORTANT: This script requires an Embeddable Python distribution.
echo Please download it and extract it into a 'python' folder
echo in this same directory before proceeding.
echo.
pause
echo.

REM --- Step 1: Check for Python ---
if not exist "python\python.exe" (
    echo [ERROR] 'python\python.exe' not found.
    echo Please check that the 'python' folder exists and contains the
    echo extracted files from the embeddable Python package.
    echo.
    pause
    exit /b 1
)
echo [OK] Python executable found.
echo.

REM --- Step 2: Guide user to enable pip ---
echo --- Automating Python Path Configuration ---
echo Automatically configuring Python environment to enable package installation.

REM Find the ._pth file
for %%F in (python\python*._pth) do (
    set PTH_FILE=%%F
)
if not defined PTH_FILE (
    echo [ERROR] Could not find the python..._pth file in the 'python' directory.
    pause
    exit /b 1
)

REM Find the python*.zip file
for %%F in (python\python*.zip) do (
    set ZIP_FILE=%%~nxF
)
if not defined ZIP_FILE (
    echo [ERROR] Could not find the python...zip file in the 'python' directory.
    pause
    exit /b 1
)

echo Found Python configuration file: %PTH_FILE%
echo Found Python library: %ZIP_FILE%

echo Backing up to %PTH_FILE%.bak
copy "%PTH_FILE%" "%PTH_FILE%.bak" > nul

echo Generating new, robust configuration for %PTH_FILE%...
(
    echo %ZIP_FILE%
    echo Lib/site-packages
    echo .
    echo import site
) > "%PTH_FILE%"

echo [OK] Configuration file updated successfully.
echo.

REM --- Step 3: Install pip ---
echo --- Downloading and installing pip ---
echo Downloading get-pip.py...
powershell -Command "Invoke-WebRequest -Uri https://bootstrap.pypa.io/get-pip.py -OutFile get-pip.py"

if not exist "get-pip.py" (
    echo [ERROR] Failed to download get-pip.py.
    echo Please download it manually from https://bootstrap.pypa.io/get-pip.py
    echo and place it in this directory, then run this script again.
    echo.
    pause
    exit /b 1
)

echo Installing pip...
python\python.exe get-pip.py

REM Check if pip was installed
if not exist "python\Scripts\pip.exe" (
    echo [ERROR] Pip installation seems to have failed.
    echo Please check for errors above.
    pause
    exit /b 1
)
echo [OK] pip installed successfully.
echo.

REM --- Step 4: Install dependencies ---
echo --- Installing required libraries ---
if not exist "requirements.txt" (
    echo [ERROR] 'requirements.txt' not found.
    echo Please make sure 'requirements.txt' is in the same directory.
    echo.
    pause
    exit /b 1
)

echo Installing libraries from requirements.txt. This may take a few minutes...
python\Scripts\pip.exe install -r requirements.txt
echo.

REM --- Step 5: Cleanup ---
del get-pip.py
echo.

echo =================================================================
echo  Setup Complete!
echo =================================================================
echo.
echo You can now run the dashboard by double-clicking the
echo 'start_dashboard.bat' file.
echo.
pause
