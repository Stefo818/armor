# Armor

Stima il rischio di cali di VWCE (10 giorni, 1, 3, 6 mesi), registra ogni previsione in un diario
che non si può modificare e la confronta ogni giorno con il risultato reale.

- Aprire il cruscotto: doppio clic su `scripts\dashboard.bat` (file `Armor_dashboard.html`)
- Aggiornare a mano: doppio clic su `scripts\aggiorna.bat`
- Primo avvio: `scripts\setup.bat`
- Dati: `data\series\*.csv` (una serie per file), `data\journal.csv` (diario), `data\outcomes.csv` (esiti)
- Online: GitHub aggiorna ogni sera (Wall Street chiusa) anche a PC spento; all'accesso a Windows il PC scarica le novità.
- Il modello e' volutamente piccolo: 8 variabili sui prezzi S&P 500 dal 1928. Nei test, aggiungere VIX e credito lo peggiorava.
- Le altre serie (VIX, credito, valutazioni...) sono mostrate come contesto e archiviate per studi futuri.
