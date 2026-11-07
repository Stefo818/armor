@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONPATH=%cd%\src
if exist .git git pull --rebase --autostash
.venv\Scripts\python -m armor tutto
if exist .git (
  git add data
  git diff --cached --quiet || (git commit -m "Aggiornamento dati" && git push)
)
if /i not "%1"=="silenzioso" (
  start "" Armor_dashboard.html
  pause
)
