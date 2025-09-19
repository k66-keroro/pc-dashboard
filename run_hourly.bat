@echo off
cd /d "C:\Users\sem3171\pc-dashboard"
python -m src.main --prod --single-run >> logs\scheduler.log 2>> logs\scheduler_error.log
