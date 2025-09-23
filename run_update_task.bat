@echo off
setlocal
cd /d %~dp0
python\python.exe -m src.main --single-run
endlocal
