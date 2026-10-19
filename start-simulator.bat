@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
.venv\Scripts\python.exe -m streamlit run robotics_app.py --server.port 8502 --server.address 127.0.0.1
pause
