@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONPATH=%cd%\src
if exist .git git pull --rebase --autostash
.venv\Scripts\python -m pip install -r requirements.txt -q
.venv\Scripts\python -m armor tutto
if exist .git (
  git add data
  git config merge.ours.driver true
  git diff --cached --quiet || (git commit -m "Aggiornamento dati" && git pull --rebase -X theirs && git push)
)
if /i not "%1"=="silenzioso" (
  start "" https://stefo818.github.io/armor/
  pause
)
