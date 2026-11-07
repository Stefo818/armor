@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONPATH=%cd%\src
.venv\Scripts\python -m armor valida
pause
