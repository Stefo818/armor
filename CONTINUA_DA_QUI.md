# CONTINUA_DA_QUI — stato del progetto Armor

Ultimo aggiornamento: 2026-11-07 (patch 15, FASE 0 del PIANO_ARMOR.md completata).

## Cosa c'è
App PWA su GitHub Pages (https://stefo818.github.io/armor/), repo Stefo818/armor. Workflow: Aggiornamento giornaliero (23:30 UTC, lun-ven), Notizie e analisi, Sito Armor (ogni 15 min), Convalida mensile, Allarmi personali, Agenda del mattino.
Pagine: Oggi, Indici, Valutazioni, Economia e Fed, Grafici, Previsioni, Contesto, Il mio VWCE, Storico, Allarmi + finestra «Assistente Armor» in basso.
Modello in uso: A1 (logistica su 8 variabili di prezzo S&P dal 1928). Indice Armor 1–100 (8 famiglie, AUC 0,72 per calo ≥10% a 3 mesi).

## FASE 0 (fatta in patch 15)
- 0.1 `sources.fetch_fred`: usa l'API ufficiale se esiste il segreto `FRED_API_KEY` (passato solo dal workflow giornaliero), altrimenti CSV pubblico; scarica solo gli ultimi ~14 mesi se la serie esiste già. `parse_fred_json`, `parse_fred_csv`.
- 0.2 Riserva se Yahoo fallisce: Stooq per `sp500` e `nasdaq100`, FRED `VIXCLS` per `vix` (`fallback_source`, `parse_stooq_csv`). Lo stato in `status.json` dice «fonte di riserva».
- 0.3 `salute.py`: tabella «Salute dei dati» in Storico + riga nel bilancio serale se una serie chiave è ferma.
- 0.4 Registro: salva anche tutte le soglie di calo/rialzo per ogni orizzonte (`dn_<hz>_<thr>`, `up_<hz>_<thr>`), scenari a 3 mesi (`scen3m_0..4`), versione modello, Indice Armor e famiglie; `registry.check()` stampa `[registro] colonne mancanti` nel log.
- Test: 24 passano (Python 3.13) e `compileall` ok con 3.11.

## Da fare dall'utente (una volta)
1. Creare la chiave su https://fred.stlouisfed.org/docs/api/api_key.html
2. GitHub → repo armor → Settings → Secrets and variables → Actions → New repository secret: `FRED_API_KEY`.

## Prossimo passo
FASE 1 del PIANO_ARMOR.md (motore FHS + validazione purged walk-forward), in due sessioni.
Nota: Stooq potrebbe richiedere una chiave in futuro; se `[dati] sp500: Yahoo non ha risposto` compare ma poi fallisce anche Stooq, controllare il log `ERR`.
