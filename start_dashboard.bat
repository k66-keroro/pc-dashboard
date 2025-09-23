@echo off
setlocal

echo =================================================================
echo  Starting PC-Dashboard
echo =================================================================
echo.

REM Change directory to the script's location
cd /d %~dp0

REM --- Sanity Checks ---
if not exist "python\python.exe" (
    echo [ERROR] Python environment not found in 'python' folder.
    echo Please run 'install_dependencies.bat' to set it up.
    echo.
    pause
    exit /b 1
)
if not exist "src\app.py" (
    echo [ERROR] Main application 'src\app.py' not found.
    pause
    exit /b 1
)
if not exist "src\main.py" (
    echo [WARNING] Data update script 'src\main.py' not found.
    echo Will start the dashboard without updating data.
    echo.
)

echo --- Starting background data update ---
if exist "src\main.py" (
    start "PC-Dashboard Data Update" /B python\python.exe src\main.py --single-run
    echo A one-time data update is running in the background.
)
echo.

echo --- Launching Dashboard GUI ---
echo A browser window should open automatically in a moment.
echo If not, open your browser and go to: http://localhost:8501
echo.
echo This window must remain open to keep the dashboard running.
echo To stop the dashboard, simply close this window.
echo.

python\python.exe -m streamlit run src\app.py --server.headless true --server.port 8501

echo.
echo Dashboard has been shut down.
pause
endlocal
