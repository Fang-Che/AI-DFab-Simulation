@echo off
cd /d "%~dp0"
py -3.12 -m venv .venv
if errorlevel 1 goto end
.venv\Scripts\python.exe -m pip install -r requirements.txt
:end
pause
