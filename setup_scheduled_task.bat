@echo off
setlocal

echo =================================================================
echo  Setup Hourly Data Update Task
echo =================================================================
echo.
echo This script will create a Windows Scheduled Task to automatically
echo update the dashboard's data every hour.
echo.
echo The task will run the data update script from the application's
echo root directory to ensure all modules are found correctly.
echo.
echo Administrator rights may be required to create scheduled tasks.
echo If this script fails, please try running it as an administrator.
echo.
pause
echo.

REM --- Define Task Details ---
set TASK_NAME="PC-Dashboard Hourly Update"

echo Creating/updating scheduled task: %TASK_NAME%
echo.

REM --- Create/Update Scheduled Task ---
REM /sd sets the starting directory for the task, which is crucial for Python's module resolution.
REM /tr specifies the executable and its arguments. The path to the executable is quoted.
schtasks /create /tn %TASK_NAME% /sc hourly /f /sd "%~dp0" /tr "\"%~dp0python\python.exe\" -m src.main --single-run"

REM --- Check for errors ---
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create the scheduled task.
    echo Please try running this script as an Administrator.
    echo.
    pause
    exit /b 1
)

echo.
echo [OK] Scheduled task %TASK_NAME% created or updated successfully!
echo.
echo You can manage this task in the Windows Task Scheduler.
echo To remove it, you can run: schtasks /delete /tn %TASK_NAME% /f
echo.
pause
endlocal
