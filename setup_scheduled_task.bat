@echo off
setlocal

echo =================================================================
echo  Setup Hourly Data Update Task
echo =================================================================
echo.
echo This script will create a Windows Scheduled Task to automatically
echo update the dashboard's data every hour.
echo.
echo The task will run the following command:
echo %~dp0python\python.exe %~dp0src\main.py --single-run
echo.
echo Administrator rights may be required to create scheduled tasks.
echo If this script fails, please try running it as an administrator.
echo.
pause
echo.

REM --- Define Task Details ---
set TASK_NAME="PC-Dashboard Hourly Update"
set TASK_RUN="%~dp0python\python.exe %~dp0src\main.py --single-run"

echo Creating/updating scheduled task with the following properties:
echo   Task Name: %TASK_NAME%
echo   Run Command: %TASK_RUN%
echo   Schedule:  HOURLY
echo.

REM --- Create/Update Scheduled Task ---
REM /f allows the task to be updated if it already exists.
schtasks /create /tn %TASK_NAME% /tr %TASK_RUN% /sc hourly /f

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
