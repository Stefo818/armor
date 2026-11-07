@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo [1/4] Creo l'ambiente Python...
if not exist .venv python -m venv .venv
echo [2/4] Installo i pacchetti (1-3 minuti)...
.venv\Scripts\python -m pip install --upgrade pip -q
.venv\Scripts\python -m pip install -r requirements.txt -q
set PYTHONPATH=%cd%\src
echo [3/4] Scarico lo storico completo di tutte le fonti (2-5 minuti)...
.venv\Scripts\python -m armor dati-completi
echo [4/4] Calcolo le previsioni e creo il cruscotto...
.venv\Scripts\python -m armor senza-download
schtasks /create /tn "Armor aggiornamento" /tr "\"%cd%\scripts\aggiorna.bat\" silenzioso" /sc onlogon /delay 0001:00 /f
start "" Armor_dashboard.html
echo.
echo FATTO. Se vedi righe ERR qui sopra, copiale e incollale a Claude.
pause
