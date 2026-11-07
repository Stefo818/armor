# CONTINUA_DA_QUI — stato del progetto Armor

Ultimo aggiornamento: 2026-11-07 (patch 16: FASE 0 fatta in patch 15; FASE 1 compiti 1.1 e 1.3 fatti in patch 16).

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

## FASE 1 — compiti 1.1 e 1.3 (patch 16)
- `src/armor/fhs.py`: motore FHS senza librerie esterne (numpy + scipy). GJR-GARCH(1,1) con errori t stimato per massima verosimiglianza (varianza con `scipy.signal.lfilter`), simulazione bootstrap di 5.000 percorsi a 126 sedute, `forecast(p, date, sims, vix, w)` con la stessa struttura di `outlook.probability_matrix` (+ `scen`, `_params`, `_sigma_annual`). `backtest_preds` = walk-forward (parametri rifatti ogni 252 sedute con dati fino a data−5). Opzione VIX: varianza del primo giorno spostata verso 0,8·VIX²/252 con peso w (nel confronto: w=0,5, «FHS+VIX»).
- `src/armor/modeleval.py` + comando `python -m armor valuta-modelli [passo]` (default 5 sedute, dal 1990): stessa regola per tutti; frequenza «normale» con soli esiti maturati (purged); A1 con fit solo su esiti maturati (purge incorporato); metriche Brier, BSS (intervallo 90% con bootstrap a blocchi di 63 sedute), log loss, AUC, taratura a 10 gruppi, BSS 1990-2012 e 2013-26. Salva `data/model_eval.json` (e `data/fhs_eval.csv` nel workflow). Passo mensile aggiunto a `valida.yml` (continue-on-error). Tempo: ~1 minuto.
- Il modello in uso resta A1 (nessun cambio, come richiesto).
- Test: 26 passano; nuovi: stima/simulazione/monotonia/no-futuro FHS, purged_base, AUC, bootstrap a blocchi.

### Risultati (1990–2026, date ogni 5 sedute, 1.830–1.855 date per bersaglio; BSS = 1 − Brier/Brier del normale; intervallo 90%)
| Bersaglio | A1 Brier | A1 BSS | A1 AUC | FHS Brier | FHS BSS [90%] | FHS AUC | BSS 2013-26 (A1 / FHS) |
|---|---|---|---|---|---|---|---|
| calo 10g ≥5% | 0,0439 | +0,055 | 0,736 | 0,0431 | +0,073 [+0,01,+0,13] | 0,760 | +0,021 / +0,006 |
| calo 1m ≥5% | 0,1336 | +0,047 | 0,680 | 0,1306 | +0,069 [+0,03,+0,11] | 0,689 | +0,025 / +0,031 |
| calo 1m ≥10% | 0,0376 | +0,061 | 0,764 | 0,0364 | +0,091 [+0,01,+0,19] | 0,797 | +0,040 / +0,046 |
| calo 3m ≥10% | 0,1141 | +0,038 | 0,673 | 0,1107 | +0,067 [+0,01,+0,14] | 0,711 | −0,033 / +0,017 |
| calo 3m ≥15% | 0,0576 | +0,024 | 0,696 | 0,0557 | +0,056 [−0,02,+0,14] | 0,702 | −0,008 / −0,031 |
| calo 6m ≥10% | 0,1716 | +0,039 | 0,638 | 0,1690 | +0,053 [+0,01,+0,12] | 0,673 | −0,077 / −0,010 |
| calo 6m ≥20% | 0,0578 | +0,062 | 0,745 | 0,0560 | +0,091 [+0,01,+0,21] | 0,720 | −0,007 / +0,015 |
| rialzo 10g ≥5% | — | — | — | 0,0326 | +0,163 [+0,12,+0,20] | 0,892 | — / +0,158 |
| rialzo 1m ≥5% | — | — | — | 0,1226 | +0,161 [+0,12,+0,20] | 0,779 | — / +0,195 |
| rialzo 3m ≥10% | — | — | — | 0,1182 | +0,147 [+0,09,+0,21] | 0,756 | — / +0,202 |
| rialzo 6m ≥10% | — | — | — | 0,2304 | +0,052 [+0,01,+0,09] | 0,635 | — / +0,070 |
| rialzo 6m ≥20% | — | — | — | 0,0592 | +0,144 [+0,03,+0,24] | 0,799 | — / +0,321 |
Lettura onesta: FHS batte A1 in Brier su tutti i cali (differenze piccole a 10g/1m, più nette a 3–6 mesi), AUC migliore quasi ovunque, e a 3–6 mesi non è mai nettamente peggio del normale (A1 sì dal 2013). I rialzi grandi sono molto più prevedibili dei cali perché dipendono soprattutto dalla volatilità. Il guadagno dal 2013 è più modesto: FHS misura la volatilità, non la direzione. Attenzione: «rialzo ≥X%» e «calo ≥X%» salgono entrambi quando la volatilità è alta (il modello non dice quale dei due prevarrà).
Taratura FHS (10 gruppi): buona al centro, leggermente troppo prudente a rischio basso e troppo ottimista agli estremi alti (es. calo 3m ≥10%: gruppo più alto previsto 0,34 → reale 0,26): serve la taratura isotonica prevista in 1.4.
Con il passo 21 (più veloce) i numeri sono molto simili.

## Da fare dall'utente (una volta)
1. Creare la chiave su https://fred.stlouisfed.org/docs/api/api_key.html
2. GitHub → repo armor → Settings → Secrets and variables → Actions → New repository secret: `FRED_API_KEY`.

## Prossimo passo
FASE 1, seconda sessione: compiti 1.2 (modello multi-variabile), 1.4 (combinazione + taratura isotonica + ritorno al normale), 1.5, 1.6. Regola di adozione in PIANO_ARMOR.md §1.4. FHS è il candidato più forte: nella combinazione avrà peso alto.
Nota: Stooq potrebbe richiedere una chiave in futuro; se `[dati] sp500: Yahoo non ha risposto` compare ma poi fallisce anche Stooq, controllare il log `ERR`.
