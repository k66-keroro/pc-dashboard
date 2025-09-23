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
set TASK_TO_RUN="%~dp0run_update_task.bat"

echo Creating/updating scheduled task: %TASK_NAME%
echo It will run this script: %TASK_TO_RUN%
echo.

REM --- Create/Update Scheduled Task ---
REM /tr points to the simple helper script. The quotes around %TASK_TO_RUN% handle spaces in the path.
REM /st sets the start time. 00:05 means it will run at 01:05, 02:05, etc.
REM /RL HIGHEST runs the task with elevated privileges.
schtasks /create /tn %TASK_NAME% /sc hourly /f /tr %TASK_TO_RUN% /st 00:05 /RL HIGHEST

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
