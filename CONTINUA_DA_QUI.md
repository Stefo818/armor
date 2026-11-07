# CONTINUA_DA_QUI — stato del progetto Armor

Ultimo aggiornamento: 2026-11-07 (patch 17: FASE 1 completa. Modello in uso: ancora A1).

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

## FASE 1 — compiti 1.2, 1.4, 1.5, 1.6 (patch 17)
**Esito della regola di adozione: NON superata. Il modello in uso resta A1.** Tentativo registrato in `data/models.json` (chiave `tentativi`, id `E1-combinato`) a ogni Convalida mensile.
- 1.2 `src/armor/model_mv.py`: modello multi-variabile dal 1990 (8 variabili sui prezzi + VIX, variazione VIX a 1 mese, VIX meno volatilità reale, spread BAA e sua variazione, curva 10Y-3M, NFCI; ritardi di pubblicazione rispettati, test no-lookahead). Due algoritmi: logistica e alberi (`monotonic_cst` dove il segno è ovvio). Non inclusi per storia troppo corta: VIX3M/VIX (dal 2006), spread HY (dal 2023), ampiezza, punteggi dell'Indice Armor.
- 1.4 `src/armor/ensemble.py`: pesi ≥0 per orizzonte (log loss fuori campione), taratura isotonica per bersaglio, ritorno al normale `w = clip(BSS 5 anni / 0,10, 0, 1)`, monotonia tra soglie. Tutto walk-forward (solo esiti maturati). Regola di adozione implementata in `ensemble.adoption` (bersaglio principale di ogni orizzonte: BSS meglio di A1 su ≥2 orizzonti sia 2000-12 sia 2013-26 e nessun peggioramento oltre 0,01).
- 1.5 intervalli all'80%: `ensemble.interval_scale/coverage` (fattore k conformale walk-forward). Copertura misurata (obiettivo 80% ± 3): FHS 81–83% a tutti gli orizzonti; A1 (quello mostrato nell'app) 81% a 10g e 1m ma **85% a 3m e 89% a 6m** (intervalli troppo larghi): l'app ora li stringe con k = 0,86 e 0,80 (copertura 80,5% e 80,1%) e scrive sotto «Verifica: in passato questo intervallo ha contenuto il risultato nel X% dei casi». Funzione `spiega.ret_display`, dati letti da `data/model_eval.json` (chiave `intervalli`). Gli scenari restano quelli di A1 (il combinato non è stato adottato).
- 1.6 `src/armor/spiega.py`: «Perché?» ora mostra le prime 3 cause per modello logistico (prima 2), una riga sul motore FHS («Volatilità attesa X% annua contro un normale di Y%») e, in `model_eval.json`, l'importanza per permutazione del modello ad alberi (3m: curva 10Y-3M, NFCI, media 50/200 giorni).
- Test: 31 passano (nuovi: no-lookahead variabili esterne, pesi/monotonia, ritorno al normale con modelli-rumore, intervalli conformali, intervallo dal vivo).
- Tempo di `valuta-modelli`: circa 2 minuti (workflow Convalida mensile, limite 45).

**Tabella finale — bersagli principali dei cali (date dal 1996 al 2026, stesse per tutti i modelli)**

| Bersaglio | Modello | Brier | BSS | AUC | BSS 2000-12 | BSS 2013-26 |
|---|---|---|---|---|---|---|
| calo 10g ≥5% | A1 | 0.0491 | +0.049 | 0.720 | +0.077 | +0.021 |
| calo 10g ≥5% | FHS | 0.0481 | +0.067 | 0.744 | +0.128 | +0.006 |
| calo 10g ≥5% | Combinato | 0.0515 | +0.001 | 0.640 | +0.005 | +0.002 |
| calo 10g ≥5% | Combinato-B | 0.0490 | +0.050 | 0.677 | +0.092 | +0.003 |
| calo 1m ≥10% | A1 | 0.0431 | +0.055 | 0.756 | +0.062 | +0.040 |
| calo 1m ≥10% | FHS | 0.0417 | +0.086 | 0.784 | +0.117 | +0.046 |
| calo 1m ≥10% | Combinato | 0.0473 | -0.038 | 0.651 | -0.067 | +0.021 |
| calo 1m ≥10% | Combinato-B | 0.0426 | +0.065 | 0.691 | +0.091 | +0.031 |
| calo 3m ≥10% | A1 | 0.1267 | +0.027 | 0.657 | +0.052 | -0.033 |
| calo 3m ≥10% | FHS | 0.1232 | +0.054 | 0.687 | +0.083 | +0.017 |
| calo 3m ≥10% | Combinato | 0.1317 | -0.011 | 0.404 | -0.006 | +0.004 |
| calo 3m ≥10% | Combinato-B | 0.1279 | +0.018 | 0.575 | +0.034 | +0.005 |
| calo 6m ≥10% | A1 | 0.1902 | +0.018 | 0.616 | +0.077 | -0.077 |
| calo 6m ≥10% | FHS | 0.1891 | +0.024 | 0.638 | +0.052 | -0.010 |
| calo 6m ≥10% | Combinato | 0.2120 | -0.094 | 0.352 | -0.124 | -0.000 |
| calo 6m ≥10% | Combinato-B | 0.1937 | +0.000 | 0.488 | +0.022 | +0.000 |

**Rialzi (A1 non li calcola)**

| Bersaglio | Modello | Brier | BSS | AUC | BSS 2000-12 | BSS 2013-26 |
|---|---|---|---|---|---|---|
| rialzo 10g ≥5% | FHS | 0.0311 | +0.180 | 0.918 | +0.199 | +0.158 |
| rialzo 10g ≥5% | Combinato | 0.0342 | +0.097 | 0.859 | +0.097 | +0.077 |
| rialzo 10g ≥5% | Combinato-B | 0.0324 | +0.146 | 0.897 | +0.173 | +0.099 |
| rialzo 1m ≥5% | FHS | 0.1217 | +0.167 | 0.785 | +0.157 | +0.195 |
| rialzo 1m ≥5% | Combinato | 0.1265 | +0.135 | 0.762 | +0.107 | +0.186 |
| rialzo 1m ≥5% | Combinato-B | 0.1232 | +0.157 | 0.780 | +0.144 | +0.195 |
| rialzo 3m ≥10% | FHS | 0.1153 | +0.156 | 0.762 | +0.102 | +0.202 |
| rialzo 3m ≥10% | Combinato | 0.1298 | +0.050 | 0.673 | -0.111 | +0.174 |
| rialzo 3m ≥10% | Combinato-B | 0.1214 | +0.111 | 0.732 | +0.023 | +0.201 |
| rialzo 6m ≥10% | FHS | 0.2308 | +0.050 | 0.630 | +0.047 | +0.070 |
| rialzo 6m ≥10% | Combinato | 0.2521 | -0.038 | 0.515 | -0.050 | +0.053 |
| rialzo 6m ≥10% | Combinato-B | 0.2407 | +0.009 | 0.552 | -0.016 | +0.049 |

**Modelli singoli (date dal 1995): multi-variabile contro A1 e FHS**

| Bersaglio | Modello | Brier | BSS | AUC | BSS 2000-12 | BSS 2013-26 |
|---|---|---|---|---|---|---|
| calo 10g ≥5% | A1 | 0.0466 | +0.052 | 0.723 | +0.077 | +0.021 |
| calo 10g ≥5% | FHS | 0.0458 | +0.070 | 0.749 | +0.128 | +0.006 |
| calo 10g ≥5% | MV-logit | 0.0480 | +0.024 | 0.750 | +0.038 | +0.024 |
| calo 10g ≥5% | MV-GBM | 0.0478 | +0.029 | 0.732 | +0.057 | +0.001 |
| calo 1m ≥10% | A1 | 0.0417 | +0.057 | 0.761 | +0.062 | +0.040 |
| calo 1m ≥10% | FHS | 0.0403 | +0.088 | 0.791 | +0.117 | +0.046 |
| calo 1m ≥10% | MV-logit | 0.0445 | -0.007 | 0.689 | -0.036 | +0.039 |
| calo 1m ≥10% | MV-GBM | 0.0445 | -0.007 | 0.691 | -0.011 | -0.004 |
| calo 3m ≥10% | A1 | 0.1221 | +0.032 | 0.668 | +0.052 | -0.033 |
| calo 3m ≥10% | FHS | 0.1185 | +0.060 | 0.701 | +0.083 | +0.017 |
| calo 3m ≥10% | MV-logit | 0.1466 | -0.163 | 0.538 | -0.100 | -0.115 |
| calo 3m ≥10% | MV-GBM | 0.1416 | -0.123 | 0.580 | -0.063 | -0.106 |
| calo 6m ≥10% | A1 | 0.1824 | +0.028 | 0.633 | +0.077 | -0.077 |
| calo 6m ≥10% | FHS | 0.1807 | +0.037 | 0.659 | +0.052 | -0.010 |
| calo 6m ≥10% | MV-logit | 0.2541 | -0.354 | 0.436 | -0.421 | -0.209 |
| calo 6m ≥10% | MV-GBM | 0.2267 | -0.208 | 0.561 | -0.109 | -0.251 |

### Lettura onesta
- Il combinato con la ricetta fissata in anticipo è PEGGIORE di A1 su tutti gli orizzonti nel 2000-12 e dà BSS negativo a 1m, 3m e 6m (6m: −0,094). Criterio di accettazione del piano (BSS ≥0 a 3 e 6 mesi) non soddisfatto.
- Cause viste nei dati: (1) la taratura isotonica si adatta troppo ai pochi casi indipendenti (le finestre si sovrappongono): da sola trasforma un +0,04 in −0,06; (2) il ritorno al normale basato sull'abilità degli ultimi 5 anni reagisce in ritardo; (3) i modelli multi-variabile sono PEGGIORI di A1 a 1m, 3m e 6m (BSS fino a −0,35): più variabili = più adattamento al rumore. La media semplice dei motori (senza taratura) è circa FHS.
- «Combinato-B» (senza taratura isotonica) è stato provato DOPO aver visto i risultati: non è adottabile (non supera comunque la regola: peggiora 10g, 3m, 6m oltre 0,01) ed è nel file solo per informazione.
- FHS da solo batte A1 nel BSS su 10g, 1m, 3m, 6m (primari) ma il piano chiede di adottare solo il combinato; FHS non è stato adottato. Domanda aperta per l'utente/Opus: nella Fase 2 o 4 valutare FHS come motore, mettendolo in «modalità ombra» (Fase 4.1) per raccogliere esiti veri prima di sostituire A1.

## Da fare dall'utente (una volta)
1. Creare la chiave su https://fred.stlouisfed.org/docs/api/api_key.html
2. GitHub → repo armor → Settings → Secrets and variables → Actions → New repository secret: `FRED_API_KEY`.

## Prossimo passo
FASE 2 del PIANO_ARMOR.md (Indice Armor più utile). Prima, decidere con l'utente se mettere FHS in modalità ombra (4.1). Non cambiare il modello in uso senza la regola di adozione.