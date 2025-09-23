@echo off
setlocal
cd /d %~dp0

REM Ensure the logs directory exists
if not exist "logs" mkdir "logs"

REM Create a timestamp for the log file, e.g., 20250923-002458
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /format:list') do set datetime=%%I
set "LOG_FILE=logs\task_run_%datetime:~0,8%-%datetime:~8,6%.log"

echo Running update task at %TIME% on %DATE%. Logging to %LOG_FILE%

REM Execute the python script, redirecting all output (stdout and stderr) to the log file
python\python.exe -m src.main --single-run --prod >> %LOG_FILE% 2>&1

endlocal
