# CONTINUA_DA_QUI — stato del progetto Armor

Ultimo aggiornamento: 2026-11-07 (patch 18: FASI 2, 3 e 4 (4.1, 4.3, 4.4) fatte. Modello in uso: ancora A1).

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

## FASI 2, 3, 4 (patch 18)
**FASE 2 — Indice Armor** (`armor_index.py`, `learning.py`, `model_mv.py`)
- 2.1 `iso_probs`: regressione isotonica (indice del giorno → evento dopo), solo esiti noti. Frase in «Oggi» e in Indici: «Con un indice a X, in passato un calo ≥10% entro 3 mesi è arrivato nel Y% dei casi (normale Z%)». Oggi: indice 50 → calo 10% a 3 mesi 16% (normale 17%).
- 2.2 `check_weights` (comando `valuta-modelli`, al massimo 1 volta l'anno, scrive `data/armor_weights.json`): pesi stimati (logistica con coefficienti ≥0, fit fino a set 2012, prova dal 2013). **Non adottati**: AUC dal 2013 peggiore o uguale su tutti e 3 gli eventi (−0,018, −0,007, +0,002). Restano i pesi fissi 22/18/8/12/12/8/6/14. `combine()` usa `weights_in_use()`.
- 2.3 le famiglie dell'Indice (6 con storia lunga; escluse «Sentimento e ampiezza» per storia corta e «Modello statistico» perché circolare), spostate del ritardo di pubblicazione (30 sedute per mensili, 5 credito, 1 le altre), entrano nel modello multi-variabile (`MVEngine(fam=True)`, modelli `MVF-logit`, `MVF-GBM`, set «famiglie» in `model_eval.json`). **Non migliorano**: a 3 e 6 mesi restano peggiori di A1 (BSS 3m −0,11/−0,05, 6m −0,32/−0,18 contro A1 +0,02/+0,01). Sono solo in ombra.
- 2.4 `learning.index_live_auc`: AUC dal vivo dell'Indice (registro giornaliero), mostrata in Storico solo con ≥40 esiti con evento (ora «in raccolta»), più tabella per fascia.
**FASE 3 — App** (`ui.py`, `report.py`, `parts.py`, `sitedata.py`, `alerts.py`)
- 3.1 «Oggi» = 5 blocchi (Cosa faccio, Indice+probabilità, Calo/Rialzo con «Perché?», P/E e P/S, Prossimo evento). Il vecchio giudizio con semafori, rischi e opportunità è in cima alla pagina Indici; i prezzi live nella pagina «Il mio VWCE e PAC».
- 3.2 pagina «Quanto fidarsi»: grafico di taratura (10 gruppi) per ogni orizzonte da `model_eval.json` (set «modelli», modello A1), BSS con intervallo, copertura intervalli, frase onesta (`ui.verdict`: «batte» solo se l'intervallo al 90% è tutto sopra 0). Oggi: nessun orizzonte batte il normale con certezza; a 3 e 6 mesi dal 2013 A1 è peggio del normale.
- 3.3 velocità: `site/series/<chiave>.json` (una serie per file, caricata solo all'apertura del grafico), `data.json` ridotto a indice (2 KB); in `index.html` c'è solo «Oggi» (59 KB, 17 KB compressi) e le altre pagine e l'Assistente si caricano da `site/pages/*.html` alla prima apertura (`build(..., lazy=True)`; il file locale `Armor_dashboard.html` resta tutto in una pagina). Service worker v7.
- 3.4 notifiche (`alerts.py`): solo cambiamenti (fascia Indice Armor, divergenza attivata, evento importante oggi/domani, previsione a 1 mese da basso/normale a elevato/alto, VWCE ±3%); massimo 1 al giorno (`pick_daily`, altrimenti elenca gli altri cambiamenti nel testo); rapporti settimanale/mensile in coda a priorità bassa (partono solo se non c'è altro); niente più bilancio serale né agenda del mattino (solo se c'è un evento importante). Gli allarmi personali sono fuori dal limite.
- 3.5 «Il mio PAC» (pagina «Il mio VWCE e PAC»): importo e data di inizio in localStorage del telefono (chiave `armor_pac_v1`), versato, valore stimato, prezzo medio di carico, effetto dei cali (tabella −5/−10/−20%), calo massimo dall'inizio. Nessun consiglio di vendita.
**FASE 4**
- 4.1 modalità ombra (`shadow.py`): ogni giorno FHS, MV-logit, MV-GBM, MVF-GBM e «Combinato (pesi)» scrivono in `data/journal_shadow.csv` (stessa catena di firme, `journal.verify(path)`). Confronto dal vivo in Storico → «Apprendimento»; serve almeno ~6 mesi. Il modello in uso resta A1.
- 4.4 rapporto mensile (`rapporto.py`): generato alla prima esecuzione giornaliera dal 1° del mese (`data/reports/mensile-AAAA-MM.json`), in Storico e nell'Assistente; comando `python -m armor rapporto-mensile`.
- 4.3 FinBERT nei modelli (`news_signal.py`): pronto e SPENTO (`ATTIVO = False`, servono ≥548 giorni di `news_sent_macro` nel registro e la regola di adozione). Per accenderlo: `ATTIVO = True` e collegare `model_mv.news_extra` in `MVEngine`. Prima data utile = prima riga del registro con tono + 18 mesi.
- Test: 39 passano. Verifica UI con Playwright a 430 px: tutte le pagine si caricano a richiesta, nessun errore in console, PAC (calcolo e persistenza dopo ricarica), grafico a finestra, Assistente e calendario funzionanti.

## PATCH 19 — Mappa settimanale e calendario interattivo (`mappa.py`)
- **Mappa settimanale dei segnali** (sostituisce la mappa mensile): una colonna per settimana, fino a 10 anni (pulsanti 1/3/5/10 anni). Righe: VWCE e S&P 500 (rendimento % della settimana, in cima), Indice Armor, 8 famiglie (con ▸ per aprire i singoli indicatori) e tutti gli indicatori (VIX, VVIX, SKEW, MOVE, curva VIX, spread, curve dei tassi, valutazioni, tendenza, AAII, ampiezza, dollaro, Sahm, sussidi, probabilità del modello, EPU). Put/Call: solo 1 giorno di storia nell'archivio, la riga compare da sola quando ci sono ≥60 giorni (`semafori._arch_series`, per ora non incluso).
- Click o mouse su un quadratino: finestra con valore reale, punteggio e colore, cosa misura, quando preoccupa, perché quel colore (zone), variazione sulla settimana prima, famiglia e peso; per l'Indice: cosa lo spinge in alto/basso; per le famiglie: indicatori che la compongono; per i rendimenti: VIX d'inizio settimana e oscillazione attesa. Tocco sul nome di una riga: scala «a che valori corrispondono i colori» (mediana dei valori reali per i punteggi 10/30/50/70/90 negli ultimi ~10 anni). Statistica descrittiva (non previsione): S&P 500 nelle 4 settimane dopo per fascia verde/rossa.
- Dati in `site/series/mappa.json` (~200 KB, 68 KB compressi) caricati solo quando la mappa è visibile. Nel file locale `Armor_dashboard.html` sono incorporati. In «Oggi» (in fondo) c'è la versione compatta (1 anno), caricata da `pages/mappa.html` con `data-lazybox` (IntersectionObserver in `parts.LAZY_CORE`); in «Indici» la versione completa.
- **Calendario**: tre viste (Giorni, Settimane, Mesi) in `site/series/cal.json` (~57 KB). Per ogni giorno/settimana/mese: previsto (tendenza storica media ± oscillazione da VIX della sera prima: giorno VIX/15,87, settimana VIX/7,1, mese VIX/3,46; per il VWCE la stessa oscillazione × rapporto di volatilità storico VWCE/S&P), reale, scostamento in punti e in σ, Indice Armor a inizio e fine periodo, probabilità di calo di Armor a inizio periodo (p_10g per settimana, p_1m per mese da `risk_history.csv`) e peggior calo realmente avvenuto. Giorni futuri: solo oscillazione attesa. Tocco su giorno/riga = dettaglio.
- Limiti dichiarati nell'app: Armor non prevede la direzione di un singolo giorno; «previsto» è la tendenza storica + oscillazione, non un modello direzionale. VWCE prima di lug 2019 = proxy VT/EURUSD.
- Servizio: service worker v8. Test: 40 passano.

## Prossimo passo
1. Controllare dopo 2-3 giorni che `data/journal_shadow.csv` cresca e che il giornaliero resti sotto i 15 minuti.
2. FASE 4.2 (taratura dal vivo) quando ci sono ≥250 previsioni scadute; confronto in ombra dopo ~6 mesi (decidere su FHS).
3. Nuova Convalida mensile: rifà `model_eval.json`, pesi (solo se è passato un anno) e prova del combinato.

## PATCH 20
- `bande.py`: fascia attesa calibrata (10°/50°/90° percentile di rendimento/(VIX/√h), solo dati noti prima di ogni anno) al posto di «±VIX/√h». Copertura 77-79% (vecchia 89-93%), fasce più strette 28-35%. Valutazione in `data/bande_eval.json`.
- Direzione su/giù: nessun indicatore testato batte la frequenza storica (BSS ≤ 0, AUC ≤ 0,5). L'app mostra fascia + frequenza storica di rialzo, non una freccia di direzione.
- `cruscotto.py`: frecce ieri / settimana fa per Indice Armor, VIX, Put/Call (archivio put/call ancora corto: «in raccolta»), termometro VIX, finestra con 3 indici (settimana/mese/3 mesi), ticker Assistente con VWCE live.
- `confronto.py`: grafico combinato giornaliero dal 2000 (S&P e VWCE tratteggiati base 100 + serie attivabili: Indice Armor, probabilità calo/rialzo, VIX, spread HY, famiglie).
- Indicatori credito (ANFCI, SLOOS, Credit-to-GDP gap, HY, BAA10Y): monitorati; entrano nell'Indice solo se il test mensile (`valuta-modelli`) li promuove (AUC +0,01 in ≥2 eventi su 3). Revisioni utili: nessuna fonte gratuita affidabile, non implementato.
- `holdings.py`: capitalizzazione in $ mld per titolo, aggiornata nel ciclo giornaliero.
- Confronto con QMRFS in Fiducia (`data/confronto_qmrfs.json`): A1 NON migliore di QMRFS; FHS (ombra) leggermente meglio ma non certo.
- sw.js cache v9.
- Da fare: lanciare `valuta-modelli` dopo che il giornaliero ha scaricato le serie FRED nuove; confrontare i motori in ombra tra ~6 mesi; aggiungere feature da opzioni (put premium) come QMRFS.

## PIANO MODELLO (dopo la patch 20)
Il piano completo per migliorare le previsioni è in `PIANO_MODELLO.md`: dati sulla salute delle aziende, storia lunga, modello a due stadi, analoghi, regole anti-illusione e regole di adozione, fasi delle patch 21-23. Script dell'analisi di partenza: `scratch/ricerca_opus/`. Copia del progetto nel cloud: `scripts/copia_cloud.py`.

## PATCH 21 (Fase A del PIANO_MODELLO: dati nuovi)
- `sources.py`: Yahoo `iwm, smh, iyt, kre, copper` (HG=F); `fetch_shiller()` restituisce anche prezzo, dividendi, utili, CPI e GS10 dal 1871.
- `fondamentali.py` (nuovo):
  - `FRED_NUOVE`: CP, DRBLACBS, CORBLACBS, DRCCLACBS, BUSLOANS, CPILFESL, PCEPILFE, T5YIFR, CFNAI, SAHMREALTIME, CCSA, PERMIT, ISRATIO, USREC, RECPROUSM156N, M2SL, NFCICREDIT/LEVERAGE/RISK, KCFSI, BAA, AAA, GS10, TB3MS, CPIAUCNS.
  - BCE CISS (giornaliero), FINRA margin debt (pagina + Excel, un tentativo), Shiller.
  - Le lente si riscaricano ogni 6 giorni (`data/fonti_lente.json`), con un tempo massimo di 200 s; se FRED fallisce 2 volte di fila si salta il resto.
  - `raccogli_revisioni()`: 30 titoli, Yahoo `eps_revisions` + `earnings_estimate`, pesati per capitalizzazione, in `rev_breadth` e `fwd_growth` (storico da oggi), dettaglio in `data/revisioni_oggi.json`.
  - `calcola()`/`aggiorna_derivate()`: eps_sp, eps_g12/g3, sales_g12, margin_sp, erp, cp_g4, cp_gdp, busloans_g6, cpi/core/core_pce yoy, infl_acc, real_ff, net_liq (miliardi) e net_liq_13w, m2_yoy, claims_up, ccsa_yoy, permit_yoy, margin_yoy, indpro_g12, sahm, curve_lunga, baa_lungo, forza relativa a 3 mesi (rel_small/eqw/cicl/semi/trasp/banche/rame_oro/credito/emergenti).
  - `LAG` (giorni dopo la data del dato) + `nota_al()` + `mensile()` (valore noto a fine mese).
- Ritardo degli utili: 150 giorni. Prova di sensibilità (calo ≥10% entro 6 mesi, 2000-2018, solo utili): con 60 giorni AUC 0,75, con 120 giorni 0,66, con 180 giorni 0,63. Gli utili mensili storici sono interpolati tra trimestri e pubblicati dopo, quindi con ritardi brevi c'era sguardo al futuro. Da ricordare in Fase B.
- `jobs.py`:
  - `fonti_nuove()` dentro `tutto` (fonti lente 240 s, revisioni 90 s); derivate sempre;
  - `dati-completi` forza le lente;
  - nuovo comando `ricerca`;
  - `valuta-modelli` prova anche i nuovi candidati.
- `semafori.py`:
  - 33 voci nuove nei gruppi «Salute delle aziende», «Inflazione», «Liquidità e leva», «Mercato interno», più CFNAI, sussidi e permessi in «Economia»;
  - insieme `MONITORATI` con etichetta «monitorato · non nell'Indice» e nota nei gruppi nuovi.
- `armor_index.py`: `NEW_IND_FOND` (21 candidati, ognuno nella sua famiglia) + `_new_items()`; `test_new_indicators` e `_apply_extra` generalizzati, stessa regola (AUC +0,01 in ≥2 eventi su 3, nessuno sotto -0,01). Prova locale: nessun candidato adottato (variazioni sotto 0,01).
- `salute.py`: 9 serie nuove nella salute dei dati.
- `ricerca.py` (nuovo) + workflow `ricerca.yml` (manuale e il 3 di ogni mese, salva `data/ricerca`):
  - dataset mensile con ritardi, obiettivi (calo10 3/6/12, calo20 12, rialzo 1/3/6/12);
  - `walk_forward` con purge, che non accetta esiti dopo il 31/12/2018 senza `holdout=True`;
  - `segnali_singoli` (soglie pre-registrate), `conteggio_segnali`, logistica per famiglia, storia lunga, `episodi`, `analoghi` (non validati);
  - registro in `data/ricerca/registro_prove.csv`.
- Prova locale con i soli dati già presenti (mancano ancora le serie nuove), 1960-2018:
  - «Solo prezzi», calo ≥10% entro 6 mesi: AUC 0,64, BSS +0,07;
  - «Storia lunga»: AUC 0,63, BSS +0,06;
  - famiglia Salute delle aziende (utili, ritardo 150 gg), 2000-2018: AUC 0,65, BSS -0,02;
  - direzione: nessun miglioramento.
- Test: 48 verdi (6 nuovi, senza rete).
- Prossimo: l'utente salva, lancia «Aggiornamento giornaliero Armor» (scarica le serie nuove) e poi `git pull`. Poi Fase B (prompt 2 del piano).

## PATCH 22 + 23 (Fase B, Fase C, prova finale) + sezione «Aziende VWCE»
**Dati arrivati**: 33 serie nuove su 34 (giornaliero dell'8/11 dopo la patch 21). Non è arrivato solo il margin debt FINRA (pagina 404): ora si provano due indirizzi (`FINRA_PAGES`). Revisioni degli utili: 30 titoli, ampiezza +23, crescita attesa +21,7%.

**Errori corretti**
- `fondamentali.calcola` si fermava con KeyError 'fedfunds' appena c'era l'inflazione di fondo. Nel giornaliero dell'8/11 nessuna serie derivata era stata aggiornata. Ora usa un defaultdict e `fedfunds` è tra gli input.
- Il registro delle prove mescolava colonne diverse: ora ha colonne fisse (`COLONNE_REG`).

**Fase B** (`ricerca.fase_b`, regole pre-registrate in testa alla sezione Fase B di `ricerca.py`)
- Modelli provati, su 8 obiettivi × 2 periodi:
  - logistica;
  - alberi monotoni con taratura di Platt (mai con pendenza negativa);
  - mesi simili (k=25);
  - famiglie combinate con pesi non negativi;
  - due stadi (recessione entro 12 mesi da USREC/NBER, purge 24 mesi, poi calo);
  - «caro + deterioramento»;
  - conteggio dei segnali.
- Riferimenti sugli stessi mesi: Solo prezzi, Indice Armor (valore grezzo), A1 (`risk_history.csv`).
- Registro: 256 combinazioni uniche (96 Fase A, 148 Fase B, 12 prova finale).

**Risultati, AUC su 100 e BSS**

1960-2018, riferimento «Solo prezzi»:

| Obiettivo | Esito |
|---|---|
| Calo ≥10% entro 3 mesi | Due stadi 71 (BSS +0,09), Famiglie 70 (+0,04), riferimento 65. **Entrambi promossi in ombra.** |
| Calo ≥10% entro 6 mesi | Migliore 64 (Famiglie), riferimento 64. Nessuno promosso. |
| Calo ≥10% entro 12 mesi | Migliore 62, riferimento 61. Nessuno promosso. |
| Calo ≥20% entro 12 mesi | Migliore 62, riferimento 66. Nessuno promosso. |

Sottoperiodi dei promossi (1960-89 / 1990-2009 / 2010-18), contro il riferimento:
- Due stadi: 67 / 82 / 49 contro 62 / 75 / 40.
- Famiglie: 66 / 78 / 62 contro 63 / 75 / 40.

2000-2018, riferimento Indice Armor (A1 a 3 mesi 74):

| Obiettivo | Migliore | Indice Armor |
|---|---|---|
| Calo ≥10% entro 3 mesi | 72 (Conteggio) | 78 |
| Calo ≥10% entro 6 mesi | 65 (Mesi simili) | 77 |
| Calo ≥10% entro 12 mesi | 68 (Due stadi) | 71 |
| Calo ≥20% entro 12 mesi | 95 (Mesi simili) | 92 |

Il 95 dei mesi simili è migliore in un solo sottoperiodo, quindi non promosso. Nessuno promosso nel 2000-2018.

Direzione: nessun modello con BSS > 0,01 su nessun orizzonte. **Resta imprevedibile.**

I mesi simili non hanno superato la regola, quindi `analoghi_validati` = falso: nell'app sono etichettati «descrittivo, non è una previsione».

Episodi 1960-2018 (Famiglie, calo ≥10% entro 12 mesi), mesi in allarme nei 12 mesi prima del massimo:

| 1966 | 1968 | 1973 | 1980 | 1987 | 2000 | 2007 |
|---|---|---|---|---|---|---|
| 12 | 10 | 3 | 7 | 0 | 0 | 5 |

In tutto 159 mesi di allarme, di cui 79 falsi.

**Prova finale 2019-2026** (`ricerca.prova_finale`, UNA volta, salvata in `data/ricerca/prova_finale.json`; se il file esiste non si rifà)

| Obiettivo | Mesi / eventi | Indice Armor | A1 | Solo prezzi | Modelli promossi |
|---|---|---|---|---|---|
| Calo ≥10% entro 3 mesi | 91 / 13 | 60 | 40 | 60 | Famiglie 46 (BSS -0,09); Due stadi 52 (BSS -0,07) |
| Calo ≥10% entro 6 mesi | 88 / 22 | 46 | 34 | 53 | — |
| Calo ≥10% entro 12 mesi | 82 / 34 | 31 | — | 43 | — |
| Calo ≥20% entro 12 mesi | 82 / 16 | 21 | — | 25 | — |

- **Adottati: nessuno.** I numeri principali dell'app non cambiano.
- Nel 2019-2026 i grandi cali (2020, 2022, 2025) sono partiti da situazioni calme, e dopo i cali il rischio misurato era alto mentre il mercato risaliva. Per questo anche l'Indice Armor e A1 a 6-12 mesi sono sotto 50.

**Fase C** (`ciclico.py`)
- `aggiorna()` gira ogni giorno in `tutto` e scrive `data/ciclico_oggi.json`:
  - stato dei 13 segnali con i valori noti oggi;
  - percentile del numero di segnali accesi dal 1990;
  - mesi simili;
  - previsioni dei modelli in ombra, anche in `data/ombra_ciclica.csv`.
- Oggi:
  - riquadro «Rischio ciclico 6-12 mesi»: segnali accesi/spenti con le frequenze 1990-2018 da `fase_b.json`; senza percentuale, perché nessun modello è adottato;
  - riquadro «Mesi del passato più simili a oggi», descrittivo.
- Quanto fidarsi: sezione «Ricerca modello» (migliore contro riferimento per obiettivo, prova finale, direzione, episodi).
- Mappa: 8 righe nuove monitorate (utili, sussidi, prestiti in ritardo, inflazione di fondo, CISS, piccole aziende, ciclici, liquidità Fed), con il percentile invertito per quelle in cui «basso = rischio».
- Lettura dell'8/11/2026:
  - 3 segnali accesi su 13 (CAPE > 30, premio utili-bond < 1%, inflazione > 4%), 55° percentile;
  - ombra a 3 mesi: Famiglie 21%, Due stadi 28%, contro una frequenza normale del 15%;
  - mesi simili: 17 su 25 in rialzo a 12 mesi, mediana +8,9%, 10 su 25 con un calo ≥10% lungo la strada.

**Aziende VWCE** (`aziende.py`, nuova pagina «Aziende VWCE»)
- Lista: 47 candidate. Peso stimato dalla capitalizzazione (riferimento `holdings.json`, altrimenti NVIDIA 5%); si tengono le prime 30.
- Bilanci Yahoo:
  - conto economico trimestrale e annuale: fatturato, utile netto, utile operativo → margine operativo;
  - stato patrimoniale: debito totale, liquidità.
- Confronto: ultimo trimestre contro lo stesso trimestre dell'anno prima (se ci sono almeno 5 trimestri), altrimenti anno fiscale contro il precedente.
- Etichetta con regola fissa: fatturato ±3%, utile ±5%, margine ±1 punto, debito netto su fatturato ±0,05. Con +2 punti «In miglioramento», con -2 o meno «In peggioramento».
- Download in `fonti_nuove()` una volta ogni 6 giorni, tempo massimo 240 s, 6 in parallelo. Se un'azienda fallisce si tiene il dato precedente (segnalato); se falliscono tutte si tiene il file precedente.
- Non ancora scaricato: il primo giro avviene nel prossimo giornaliero.

**Altro**
- Comando `ricerca-finale` (mostra il risultato salvato).
- `ricerca.run()` = Fase A + Fase B: il workflow mensile rifà la ricerca ma non la prova finale.
- `sw.js` v10. Test 54 verdi.

**Prossimo**
- Controllare la prima esecuzione di Aziende VWCE (riga `[aziende]` nel log) e del margin debt.
- Tra circa 6 mesi confrontare `ombra_ciclica.csv` con gli esiti reali.
- I modelli promossi in futuro dalla ricerca mensile restano in ombra: per adottarli servirebbe una nuova prova su anni non usati (dopo il 2026).

## PATCH 24 (tasto aggiorna, dati sempre aggiornati, VWCE serale, trimestrali chiare, contratti firmati, motore per orizzonte)
- **Tasto «⟳ Aggiorna dati»** (`forza.py`, in alto a destra su tutte le pagine):
  - avvia via API GitHub `site.yml` (prezzi + pagina, 3-5 min) oppure `daily.yml` (tutto, 20-30 min);
  - segue lo stato ogni 20 s; dopo il giornaliero aspetta anche la ricostruzione del sito e poi ricarica;
  - serve una chiave GitHub «fine-grained» (solo repository armor, permesso Actions: Read and write), salvata solo nel browser del telefono (`localStorage armor_gh_token`);
  - banner «Dati non aggiornati» se una serie chiave è ferma (`salute.compute`, luce rossa).
- **Dati sempre aggiornati**:
  - `site.yml`: nuove esecuzioni alle 22:05 e 22:35 UTC (dopo le 23 italiane, chiusura di Lang & Schwarz); si ricostruisce dopo ogni workflow di dati (giornaliero, notizie, ricerca, convalida, mattino);
  - `daily.yml`: giro di riserva alle 04:40 UTC (mar-sab);
  - bilanci delle aziende riletti ogni giorno (`GIORNI = 1`);
  - `sw.js` v11: le chiamate ad altri siti (API GitHub) non passano mai dalla cache.
- **VWCE serale** (`live.py`):
  - oltre alle 7 sedi Yahoo (Xetra 17:30, Stoccarda/gettex fino alle 22), si provano onvista (`api.onvista.de` snapshot, più sedi con orario, compresa Lang & Schwarz fino alle 23) e Tradegate (`refresh.php`, ora non indicata: usata solo con scambi del giorno, con ora = adesso o le 22:00);
  - vince l'ultimo scambio entro ±3% da Xetra;
  - nel log: riga `[live] VWCE: prezzo da sede alle ora · sedi lette: …`.
  - Le due fonti nuove NON sono verificabili da qui (rete bloccata): controllare la riga `[live]` nel log di «Sito Armor». Se onvista e Tradegate non rispondono, resta l'ultima sede Yahoo (di solito 21:30-22:00).
- **Aziende VWCE**:
  - sempre l'ultima trimestrale con i mesi esatti (es. «lug-set 2026, 3 mesi»); le semestrali (aziende europee) sono indicate come tali;
  - confronto con lo stesso periodo di un anno prima, oppure con il periodo precedente, dichiarato;
  - elenco «Aumentati / Diminuiti»;
  - ultimo anno fiscale separato.
  - Fatturato 12 mesi = somma degli ultimi 4 trimestri (o 2 semestri, o anno fiscale).
  - Nuovi rapporti: capitalizzazione/fatturato 12 mesi e capitalizzazione/(fatturato 12 mesi + contratti già firmati non ancora fatturati, RPO), con anni di fatturato coperti e crescita annua dei contratti.
  - RPO dalla SEC (`data.sec.gov` companyconcept: us-gaap RevenueRemainingPerformanceObligation o ifrs-full TransactionPriceAllocatedToRemainingPerformanceObligations), richieste in fila con User-Agent «Armor personal research armor-bot@users.noreply.github.com» (variabile `SEC_USER_AGENT` per cambiarlo). Dove l'azienda non li pubblica: «non pubblicati».
- **Un motore per ogni orizzonte** (`campioni.py`, `data/campioni.json`, rifatto in `valuta-modelli`):
  - regola: uno sfidante (FHS, FHS+VIX) sostituisce A1 se il BSS è migliore di almeno 0,005 sia nel 2000-2012 sia nel 2013-oggi, l'AUC non è peggiore di oltre 0,01 e le altre soglie non peggiorano; vince il migliore nel sottoperiodo peggiore;
  - esito sulla valutazione del 7/11/2026:

    | Orizzonte | Motore | BSS 2000-12 | BSS 2013-26 | Battuto |
    |---|---|---|---|---|
    | 10 giorni | A1 | — | — | FHS peggiore nel 2013-26 (0,006 contro 0,021) |
    | 1 mese | FHS+VIX | 0,113 | 0,052 | A1: 0,062 / 0,040 |
    | 3 mesi | FHS+VIX | 0,084 | 0,020 | A1: 0,052 / -0,033 |
    | 6 mesi | A1 | — | — | FHS peggiore nel 2000-12 |

  - Coerenza: la probabilità di un calo entro un orizzonte più lungo non può essere più bassa della stessa soglia a un orizzonte più breve (si alza e si annota).
  - Il diario registra `A1+FHSV(1m,3m)`; la modalità ombra riceve sempre le stime di A1 puro.
  - Le schede delle previsioni indicano il motore e la stima di A1.
  - Le parole delle schede non dicono più «tranquillo» quando il rischio è sopra il solito.
  - Esempio dell'8/11: calo ≥10% entro 1 mese 11% (A1 3%), entro 3 mesi 24% (A1 8%), entro 6 mesi alzato a 24% per coerenza.
  - È una scelta fatta guardando la valutazione esistente (un po' di scelta a posteriori): la modalità ombra continua e la regola si rifà ogni mese.
- Test: 58 verdi.

## PATCH 25 (lista dei semafori cliccabile)
- `semafori.lista_html()` crea la finestra `#semmod` con tutti i semafori divisi per colore: a rischio (rosso), attenzione (giallo), tranquilli (verde), solo informativi.
  - Filtri in alto; dentro ogni sezione l'ordine è dal percentile più estremo.
  - Ogni riga mostra nome, famiglia, «monitorato», data del dato, percentile, soglie (per rossi e gialli) e valore.
  - Toccando una riga si apre il grafico; un pulsante porta alle schede complete in Indici.
- Si apre con qualsiasi elemento `data-semlist='all|ba|wa|ok'` (`LISTA_JS`, gestore unico sul documento, funziona anche nell'Assistente caricato dopo).
  - Bilancio del giorno: `bilancio.day_html` rende cliccabili «N rossi, N gialli, N verdi» + «vedi la lista» con `semafori.cliccabile()`, anche sui bilanci già salvati.
  - Oggi: nuova riga «Semafori di oggi» sotto gli indici principali.
  - Indici: i conteggi in cima sono cliccabili.
- Nota: il bilancio del giorno conta i semafori all'ora del giornaliero, la lista mostra i valori al momento della pagina, quindi i numeri possono differire di poco.
- `sw.js` v12. Test 59 verdi.

## PIANO ARMOR 3 (dopo la patch 25)
Il piano successivo è in `PIANO_ARMOR3.md`: sintesi delle revisioni di Claude, GPT, Gemini e DeepSeek più due misure sul codice reale.
- Misure: persistenza del GARCH 0,989 (emivita circa 63 sedute); a 252 sedute centro della distribuzione e probabilità di calo corretti, ma code che esplodono (curtosi 50-75 contro 1-3 storica).
- Fasi: 0 (A1 di nuovo riferimento, FHS+VIX sperimentale affiancato), 1 (verifica rigorosa e protocollo), 2+7 (motore unico di percorsi e diario v3), 3 (VWCE in euro), 4 (affidabilità), 5 (simulatore PAC), 6 (esperimenti VRP/HAR).

## PATCH 26 (Fase 0 del PIANO ARMOR 3: A1 di nuovo numero principale)
- `jobs.forecast()` non sostituisce più le probabilità: A1 è il riferimento ufficiale a tutti gli orizzonti e il diario registra `model=A1`.
- `campioni.sfidante()` calcola FHS+VIX (peso 0,5, VIX dell'ultima seduta entro 7 giorni) e lo salva in `pred[hz]['sfidante']` = `{motore, p, div, vix}`. `campioni.applica()` resta solo per i test.
- Badge «Divergenza» (`campioni.divergenza`): |sfidante − A1| ≥ 5 punti e rapporto ≥ 2 sulla soglia principale. Le schede (`chiaro.horizon_simple`) mostrano «Sperimentale: modello in prova (FHS+VIX) X% (A1: Y%)» e la spiegazione. Nessuna media.
- `campioni.avvisi_coerenza()`: solo avviso se A1 non è monotono tra orizzonti, senza toccare i numeri.
- Diario ombra: FHS+VIX aggiunto accanto a FHS (`shadow.predictions`, nome `FHS+VIX`).
- «Quanto fidarsi»: la sezione si chiama «Sfidanti in prova»; testo: la scelta fu fatta guardando la stessa valutazione, non è una prova; revisione descrittiva il **10 maggio 2027**, nessuna promozione automatica.
- Nuovi download (solo in GitHub Actions): `vix6m` (^VIX6M), `vix1y` (^VIX1Y) con Yahoo; `dexuseu` (FRED DEXUSEU); `sp_open`, `sp_high`, `sp_low` (^GSPC dal 1990, una sola richiesta, `sources.fetch_sp_ohlc`). Se non arrivano il ciclo continua: serviranno a Fase 2 (curva VIX), Fase 3 (euro) e Fase 6a (Yang-Zhang). **Non verificati da qui (rete bloccata): controllare i log di «Aggiornamento giornaliero Armor».**
- `sw.js` v13. Test 60 verdi.

## PATCH 27 (Fase 1 del PIANO ARMOR 3: revisione del codice, verifica.py, protocollo)
### 1a. Rapporto di revisione del codice (nessun errore grave trovato; test in `test_revisione_codice_definizioni_e_purge`)
| Punto | Esito |
|---|---|
| `features.fwd_maxdd` | **Corretto, ma nome fuorviante**: è il calo massimo rispetto al prezzo di OGGI nelle h sedute successive (minimo/prezzo − 1), non il massimo drawdown. Dichiarato nel protocollo; il massimo drawdown vero è un obiettivo separato nel motore di percorsi (Fase 2). |
| «10 giorni» | = 7 sedute (circa 10 giorni di calendario). Corretto e coerente ovunque (`config.HORIZONS`). |
| Purge in `Engine.fit` e `modeleval.purged_base` | **Corretto**: addestramento con le sole righe la cui finestra futura finisce entro la data (data ≤ t − h); base «normale» = esiti maturati. Testato. |
| `modeleval`, `fhs.backtest_preds` | Corretto: parametri rifatti ogni anno con embargo di 5 sedute, varianza aggiornata con i prezzi noti. |
| `data/risk_history.csv` | Walk-forward senza sguardo al futuro (rifit ogni 63 sedute; base ferma tra un rifit e l'altro, ma causale). **Limite**: usa `champion_engine`, oggi A1; se in passato fosse stato scelto un campione con variabili extra, la scelta sarebbe a posteriori. |
| `features.vwce_series` | **Corretto**: livello in euro = livello VT in dollari / EURUSD (dollari per euro); testato con un caso numerico. Limiti da dichiarare: VT segue il FTSE Global All Cap (non All-World), chiude alle 22:00 contro le 17:30 di VWCE.DE (la giunzione usa un solo giorno di scala), ritenute sui dividendi diverse; VT con `auto_adjust=True` rende il rendimento con dividendi lordi. Si rifà con segmenti dichiarati nella Fase 3. |
| `fondamentali.LAG` | Utili/margini 150 giorni (realistico); mensili con ritardi dichiarati. Dati FRED **rivisti** (non in tempo reale): limite da dichiarare. |
| Pesi dell'Indice Armor (22/18/8/12/12/8/6/14) | **Limite**: scelti nel 2026 guardando la storia (adattamento a posteriori). Sono presentati come descrittivi, non come previsione verificata. |
### 1b. `verifica.py` (nuovo)
Brier, BSS, log loss, AUC, curva a 10 classi, errore di calibrazione, pendenza di calibrazione; finestre non sovrapposte (tutti gli sfasamenti); bootstrap stazionario (2.000 repliche, blocco medio ⌈h/5⌉); episodi; Diebold-Mariano con errori HAC e Holm; PBO con CSCV; copertura delle fasce, CRPS dai quantili, QLIKE; `regola_adozione()` con le soglie del protocollo. Test su dati sintetici con risultato noto (PBO ≈ 0,5 su configurazioni casuali, Holm su esempio noto, ecc.).
### 1c. Verifica rifatta 1994-oggi (una data ogni 5 sedute; 1.650 date; bootstrap 1.000 repliche) — `data/verifica_storica.json`, comando `python -m armor verifica` (rifatta ogni mese da `valuta-modelli`)
Calo (BSS rispetto alla frequenza storica con intervallo al 90%; episodi = crisi distinte):

| Bersaglio | Episodi | A1 | FHS | FHS+VIX | Differenza di Brier FHS+VIX − A1 [90%], p Holm |
|---|---|---|---|---|---|
| ≥5% in 7 sedute | 64 | +0,071 [+0,03; +0,12] | +0,100 | +0,100 [+0,06; +0,15] | −0,002 [−0,003; −0,000], p 0,077 |
| ≥5% in 21 sedute | 62 | +0,049 [+0,01; +0,09] | +0,064 | +0,070 | −0,003 [−0,006; −0,000], p 0,33 |
| ≥10% in 21 sedute | 20 | +0,048 [−0,01; +0,11] | +0,065 | +0,069 [+0,00; +0,13] | −0,001 [−0,002; +0,001], p 1,0 |
| ≥10% in 63 sedute | 15 | +0,031 [−0,05; +0,12] | +0,054 | +0,053 [−0,00; +0,12] | −0,003 [−0,009; +0,003], p 1,0 |
| ≥15% in 63 sedute | 13 | +0,030 | +0,072 | +0,067 | p 0,91 |
| ≥10% in 126 sedute | 12 | +0,034 [−0,05; +0,12] | +0,043 | +0,047 | −0,002 [−0,014; +0,010], p 1,0 |
| ≥20% in 126 sedute | 4 | +0,044 | +0,058 | +0,055 | p 1,0 |

- **Conclusione onesta**: la differenza FHS+VIX contro A1 (patch 24) **non è statisticamente solida** a 1, 3 e 6 mesi; solo a 7 sedute c'è un vantaggio piccolo (p con Holm 0,077). A1 stesso, alle soglie ≥10%, ha intervalli del BSS che includono lo zero: a 3-6 mesi non si distingue dalla frequenza storica. Pendenze di calibrazione: A1 0,64-0,88 (probabilità troppo estreme); FHS+VIX 0,86-1,03 (meglio).
- Indice Armor (logistica a una variabile, 2005-oggi, meno date): BSS +0,076 / +0,053 / +0,065 / +0,017 / −0,067 a 7/21/21/63/126 sedute; a 6 mesi peggiore della frequenza storica (pendenza 0,37).
- «Solo prezzi» (dd252, ma200, mom63): simile ad A1 (BSS 0,02-0,04), peggiore a 7 sedute (p Holm 0,08).
- PBO tra A1/Solo prezzi/FHS/FHS+VIX: 0,08 (7 sedute), 0,18 (5% 21 s), 0,74-0,96 (soglie alte): a lungo orizzonte il «migliore in campione» è spesso sotto la mediana fuori campione, cioè non c'è un vincitore stabile.
### 1d. `PROTOCOLLO_VERIFICA.md` (nuovo, versione 1 dell'8/11/2026)
Contiene ruoli, dati e metodo, le 12 varianti pre-registrate (V0-V2 × T0-T3), la **regola di adozione storica** (5 condizioni, Holm su 12, scelta tra varianti per CRPS → calibrazione → semplicità), conferma dal vivo (revisione descrittiva 10/5/2027, prima decisione 8/11/2028, finestre minime 24/8/4) e regola di ritorno ad A1. L'impronta SHA-256 viene scritta da `verifica.registra_protocollo()` in `data/protocollo_log.csv` al primo ciclo giornaliero dopo il rilascio.
### In app
«Quanto fidarsi» → nuova sezione «Verifica storica con margini d'errore» (tabella per bersaglio con BSS [90%], AUC, pendenza, differenza di Brier da A1 e p con Holm). Test 63 verdi.

## PATCH 28-29 (Fasi 2 e 7: motore unico di percorsi, 12 varianti, diario v3)
### Codice
- `percorsi.py`: dagli stessi percorsi (20.000 live, seme fisso per data, stessi numeri casuali per orizzonti e varianti) escono rendimento finale (quantili 5-95, P<0), perdita da oggi (soglie 5/10/15/20) e massimo drawdown. Orizzonti 5, 7, 21, 63, 126, 252 sedute. Errore Monte Carlo salvato (mostrato se > 0,5 punti); persistenza ed emivita del GARCH a ogni stima (oggi 0,989 → circa 63 sedute); curva della volatilità attesa a 252 sedute.
- 12 varianti pre-registrate (V0/V1/V2 × T0/T1/T2/T3), definizioni nel docstring e in PROTOCOLLO_VERIFICA.md §3. Test: coerenza per costruzione (orizzonti, soglie, drawdown ≥ perdita), caso deterministico, controllo delle code, V2 senza VIX3M non esiste, rapporti realizzata/implicita senza sguardo al futuro.
- `journal3.py` / `data/journal_v3.csv`: solo aggiunte, catena di hash, una riga per data/modello con versione del codice, parametri, ingressi (VIX, rapporti, data dell'ultimo dato di ogni serie chiave), tutte le probabilità e i quantili con errore MC; esiti in righe separate a scadenza (6 orizzonti). `journal3.verify()` chiamato nel ciclo giornaliero. Test con manomissione.
- Ciclo giornaliero: `percorsi.oggi()` (scrive `data/percorsi_oggi.json`), `percorsi.applica_adozione()` (cambia i numeri principali SOLO dove `data/adozione.json` indica una variante adottata), righe nel diario v3 per A1 e per la variante mostrata.
- App: «Scenari da 1 settimana a 1 anno» in Previsioni; «Motore di percorsi: regola di adozione» in Quanto fidarsi. Comando `python -m armor verifica-percorsi` (~15 min con il walk-forward, rifacibile).
### Verifica walk-forward 1994-oggi (1.650 date, 3.000 percorsi, parametri rifatti ogni anno) — `data/percorsi_verifica.json`, 48 prove nel registro
**Esito della regola di adozione: NESSUNA variante passa a nessun orizzonte. A1 resta il numero principale a tutti gli orizzonti** (`data/adozione.json` senza varianti adottate).
| Orizzonte | A1 BSS / pendenza | Miglior variante per CRPS | Differenza di Brier da A1 [90%], p Holm | BSS 94-12 / 13-oggi | Pendenza | Copertura 10-90 |
|---|---|---|---|---|---|---|
| 7 sedute (≥5%) | +0,071 / 1,01 | V1T0 | −0,0014 [−0,0026; −0,0003], 0,31 | +0,13 / +0,04 | 1,01 | 84% |
| 21 (≥10%) | +0,048 / 0,88 | V1T1 | −0,0004 [−0,0019; +0,0011], 1,0 | +0,08 / +0,02 | 0,90 | 84% |
| 63 (≥10%) | +0,031 / 0,71 | V1T1 | −0,0019 [−0,0084; +0,0046], 1,0 | +0,07 / 0,00 | 0,93 | 84% |
| 126 (≥10%) | +0,034 / 0,64 | V1T1 | −0,0012 [−0,0133; +0,0117], 1,0 | +0,07 / −0,01 | 1,04 | 84% |
- A 7 sedute l'intervallo è a favore delle varianti V0/V1 senza controllo, ma Holm (p 0,31) e PBO (0,76) bloccano; a 1-3-6 mesi gli intervalli includono lo zero.
- **Cosa migliora davvero (senza che passi la regola)**: calibrazione (pendenza 0,90-1,04 contro 0,64-0,88 di A1 a 1-6 mesi), fasce del rendimento ben centrate (copertura 10-90 tra 80 e 85%, 5-95 tra 91 e 94%), probabilità coerenti tra orizzonti e soglie, tre obiettivi dagli stessi percorsi.
- PBO tra le 12 varianti: 0,76 / 0,38 / 0,80 / 0,67; con le sole varianti con tutte le date 1,0 / 0,80 / 0,98 / 0,92. Le varianti sono quasi lo stesso modello (molto correlate), quindi il «migliore in campione» è praticamente casuale: coerente con l'assenza di un vincitore.
- **V2 (struttura a termine VIX/VIX3M) è peggiore**: a 3-6 mesi BSS negativo (fino a −0,19) e pendenza 0,16-0,38; il VIX3M esiste solo dal 2006 (copre 61-62% delle date di A1, quindi per protocollo non poteva essere adottato). Risultato negativo registrato.
- T3 (blocchi riscalati) è troppo largo/prudente (copertura 89-92%, pendenza 0,4-0,9 a 1 mese); T1 (tetto) e T0 quasi uguali a 7-21 sedute; T2 = T0 fino al giorno 63.
- **Controllo delle code (oggi, 20.000 percorsi a 252 sedute, curtosi in eccesso; storica a finestre non sovrapposte 126 sedute 2,9 e 252 sedute 1,2)**: T0 85 / 51 (percorsi da −100% a +2.941%); **T1 4,2 / 3,4 (min −74%, max +109%)**; T2 9,9 / 4,4; T3 0 (code sottili). La variante mostrata come sperimentale è **V1T1** (FHS+VIX con tetto alla varianza): CRPS medio normalizzato più basso (1,00003) tra le varianti con tutte le date.
- Oggi (8/11 dati del 6/11, V1T1): perdita ≥10% da oggi 11% (1 mese), 25% (3 mesi), 32% (6 mesi), 39% (1 anno); chiudere in negativo 42% / 36% / 31% / 27% (storico 38% / 33% / 29% / 25%).
### Dati nuovi (richiesta dell'utente dopo la patch 27)
- Dopo la patch 26 non c'era ancora un giornaliero lanciato: in `data/series` mancano ancora `vix6m`, `vix1y`, `dexuseu`, `sp_open/high/low`. **Non verificabile da qui se Yahoo abbia ^VIX6M/^VIX1Y.** Se mancano, l'esperimento VRP (Fase 6a) usa solo VIX/VIX3M e l'OHLC di ^GSPC; se manca anche l'OHLC si farà quando i dati arriveranno (workflow «Ricerca modello Armor»). Piano B euro: `eurusd` di Yahoo (già presente) al posto di DEXUSEU.
- File `top_ps.csv`, `top_pe.csv`, `top_fcf_yield.csv` (52 byte): NON sono vuoti, contengono 2 righe (7 e 8/11/2026): sono serie istantanee che si accumulano un giorno alla volta, quindi corte per costruzione.

## PATCH 30 (Fase 3: VWCE in euro con segmenti dichiarati)
- `serie_eur.py`: livello in euro = livello in dollari ÷ F (dollari per euro); F = DEXUSEU se presente, altrimenti EURUSD=X di Yahoo (oggi: **EURUSD=X**, perché `dexuseu` non è ancora scaricato). Test con un caso numerico (F noto) e verifica 1 + r€ = (1 + r$)·F(t−1)/F(t).
- Segmenti dichiarati (`data/serie_eur.json`): (b) VT convertito in euro 26/06/2008 → 28/07/2019; (a) VWCE.DE reale dal **29/07/2019** (primo dato scaricato; il piano diceva 23/07); (c) S&P 500 in euro dal 01/12/2003, solo robustezza, mai chiamato VWCE. Limiti scritti in app (FTSE Global All Cap contro All-World, orari di chiusura, ritenute).
- Sovrapposizione 2019-08 → oggi (379 settimane): correlazione dei rendimenti settimanali VT-euro / VWCE **0,89**; differenza di rendimento annuo (VWCE − VT in euro) +0,3 punti; volatilità annua 15% contro 16%. Quindi il segmento prima del 2019 è una stima.
- Motore di percorsi stimato sui rendimenti di VWCE in euro (V0T1, senza VIX; 4.640 giorni dal 2008): `serie_eur.oggi()` ogni giorno, `data/percorsi_eur_oggi.json`. Oggi: perdita ≥10% da oggi 8% (1 mese), 19% (3 mesi); chiudere in negativo 37% / 31%.
- **Confronto sugli esiti reali di VWCE in euro (luglio 2011-oggi, V0T1, 2.000 percorsi, perdita da oggi)**:

  | Esito | Episodi | BSS motore S&P in dollari | BSS motore su VWCE in euro | Differenza di Brier (euro − dollari) [90%] |
  |---|---|---|---|---|
  | calo ≥5% in 1 mese | 26 | +0,038 | −0,001 | +0,0046 [−0,0014; +0,0102], p 0,19 |
  | calo ≥10% in 1 mese | 6 | −0,015 | −0,031 | +0,0005 [−0,0011; +0,0020], p 0,63 |
  | calo ≥10% in 3 mesi | 7 | +0,010 | −0,095 | +0,0097 [−0,0003; +0,0205], p 0,07 |

  Conclusione: il motore sull'S&P 500 in dollari (storia dal 1950) prevede almeno altrettanto bene gli esiti di VWCE in euro; nessuna differenza è netta (pochi episodi), quello in euro resta un controllo. Il riferimento non cambia.
- App: «Quanto fidarsi» → nuova sezione «VWCE in euro» (segmenti, sovrapposizione, scenari in euro, confronto tra motori). Comando `python -m armor serie-euro`; rifatto ogni mese da `valuta-modelli`.
- Non fatto (bassa priorità, non verificabile da qui): scarico delle partecipazioni e dei pesi per paese dal sito Vanguard. Restano le stime «dalla capitalizzazione».
- Test 70 verdi.

## PATCH 31 (Fase 4: indice di affidabilità a segnali)
- `affidabilita.py`: cinque segnali con soglie fissate prima, nessun peso inventato; mostrati uno per uno in Oggi («Quanto è affidabile la stima di oggi»), salvati in `data/affidabilita.json` ogni giorno:
  1. Disaccordo: |FHS+VIX − A1| ≥ 5 punti e rapporto ≥ 2 su una soglia principale (`campioni.divergenza`).
  2. Dati vecchi: almeno una serie di `salute.KEY_SERIES` rossa.
  3. Situazione mai vista: distanza di Mahalanobis dello stato di oggi (8 variabili di A1 + VIX + spread BAA-10Y + curva 10Y-3M, dal 1990) oltre il 99° percentile delle distanze storiche.
  4. Errori recenti: Brier delle previsioni scadute del diario (1 mese, una per finestra non sovrapposta) peggiore della frequenza storica; attivo solo con almeno 12 finestre (oggi 1: «non ancora valutabile»).
  5. Instabilità: la probabilità principale a 1 o 3 mesi cambia di oltre 3 punti stimando il GARCH dal 1950, dal 1990 o sugli ultimi 15 anni.
- Livello: 0 segnali accesi = alta, 1 = media, 2 o più = bassa con l'avviso «Stima poco affidabile: …». Un segnale non valutabile non conta.
- Oggi (dati del 6/11/2026): **affidabilità bassa**: disaccordo (A1 5% contro 14% a 10 giorni, 3% contro 11% a 1 mese, 8% contro 24% a 3 mesi, 15% contro 32% a 6 mesi) e instabilità (a 1 mese la stima va da 12% a 20% secondo la storia usata); situazione mai vista spenta (distanza 4,1 contro soglia 8,9); dati: nessuna serie chiave rossa.
- Test: ogni segnale e il livello, instabilità con GARCH simulato, Mahalanobis su dati normali. 72 verdi.

## PATCH 32 (Fase 5: simulatore del PAC)
- `pacsim.py`: 1.000 percorsi di rendimenti mensili di VWCE **in euro** per 60 mesi (`data/pac_sim.json`, ~250 KB, copiato in `site/pac_sim.json`, rifatto ogni giorno con seme fisso per data): mesi 1-12 dal motore di percorsi condizionato a oggi (V0T1 stimato sui rendimenti di VWCE in euro, a blocchi di 21 sedute); mesi 13-60 bootstrap stazionario (blocco medio 6 mesi) dei rendimenti mensili storici in euro (221 mesi dal 2008; media storica **10,6% all'anno**: periodo favorevole alle azioni, dichiarato in app).
- App (Il mio VWCE e PAC → «Simulatore del PAC»): capitale, versamento mensile, giorno di acquisto (1-28; più tardi nel mese = meno rendimento nel primo mese), costo per acquisto, TER; dati salvati solo nel browser (`armor_pacsim_v1`). Due scenari sempre insieme: «storico» e «prudente» (−3 punti all'anno). A 1, 3 e 5 anni: percentili 5/25/50/75/95 del patrimonio, probabilità di stare sotto il versato, calo massimo del patrimonio (mediana e caso brutto al 10%).
- Confronto «continuo / sospendo 3 o 6 mesi» con le due ipotesi dette in chiaro (liquidità ferma, oppure investita tutta alla ripresa); il simulatore non suggerisce mai di sospendere. Esempio (5.000 € + 200 €/mese, scenario storico, a 5 anni): continuo senza pause mediana 24.370 €; sospendo 3 mesi con soldi fermi 23.935 € (meglio del «continuo» nel 7% dei percorsi), tutto investito alla ripresa 24.364 € (28%).
- TER predefinito **0,14%**: valore trovato su una fonte di stampa italiana (risparmioggi.it, 22/07/2026: dal 28/07/2026; prima 0,19%). **Da verificare sulla scheda Vanguard**, modificabile in app. I rendimenti storici del segmento VWCE sono già netti del costo, quindi applicarlo per intero è prudente.
- Messaggio per chi accumula in app: «i cali dei primi anni comprano più quote; il rischio pesa di più vicino al momento in cui si disinveste».
- Test: caso deterministico (rendimento costante → valore in forma chiusa), TER, costo per acquisto, scenario prudente, giorno di acquisto, sospensione, drawdown; percorsi senza valori oltre i limiti e con seme fisso; **JavaScript identico al Python** (test con browser). 75 test verdi. `sw.js` v14.

## PATCH 32-bis (controllo A sul simulatore del PAC)
- Nel simulatore `C` è il **valore di mercato oggi** di ciò che si possiede, NON il versato. Aggiunto il campo facoltativo «Costo storico» (`pskc`, parametro `K` in `pacsim.patrimonio`): «versato» = K + rata × mesi; se vuoto K = C (come prima). Etichette in app chiarite. Il valore del patrimonio non dipende da K (cambia solo il confronto «sotto il versato»).

## PATCH 33 (Fase 6a: esperimento VRP e HAR, in ombra)
- Regole scritte prima in `PROTOCOLLO_VRP.md` (impronta in `data/protocollo_vrp_log.csv`). Codice `vrp.py`, comando `python -m armor esperimento-vrp` (step nel workflow «Ricerca modello Armor», ~10 minuti, `continue-on-error`), risultati `data/vrp_ombra.json`, prove nel registro (`tipo = vrp1`), sezione «Esperimento: premio di volatilità» in Quanto fidarsi.
- Dati: apertura/massimo/minimo di ^GSPC da Yahoo. **Qualità**: prima del 2005 l'apertura coincide con la chiusura precedente (>93% dei giorni) → esperimento solo dal 2008; valutazione ogni 5 sedute dal 2011-01-03 (786 date). ^VIX1Y non esiste su Yahoo (nessun dato), ^VIX6M dal 2008 sì.
- Previsione di volatilità a 21 sedute (QLIKE, più basso meglio; differenza contro VIX [90%], Holm): VIX 0,391; HAR 0,303 (−0,088 [−0,130; −0,038], p 0,002); HAR+VIX 0,267 (−0,124 [−0,177; −0,057], p 0,001); VIX meno premio medio 0,455 (+0,064 [−0,042; +0,185], p 0,34). Il VIX sovrastima la varianza realizzata in media di 2,7 volte (premio al rischio).
- Probabilità (5 esiti, contro FHS+VIX; ΔBrier negativo = meglio): nessun modello ha l'intervallo tutto a favore su ≥3 esiti con Holm<0,10 → **«nessun vantaggio dimostrato»**. Il solo VIX come varianza è peggiore (calo ≥5% in 1 mese: +0,0047 [+0,0013; +0,0080]); VIX meno premio è peggio e poco calibrato (copertura 10-90 al 73%); HAR+VIX è a metà strada: meglio sulla chiusura in negativo a 1 e 3 mesi (−0,0009 e −0,0014, Holm 0,13 e 0,08) ma non sui cali. Resta tutto in ombra. Conclusione: prevedere meglio la volatilità non si traduce in probabilità di calo migliori con questo campione corto (15 anni, pochi episodi).
- Test 77 verdi. Se in futuro arrivasse ^VIX1Y o un'apertura vera pre-2008, serve un protocollo nuovo (versione 2).

## PATCH 34 (automazione e auto-diagnostica; riquadro «Quanto fidarsi» riscritto)
- **Riquadro affidabilità** (`affidabilita.py`, pagina Oggi): ora ha verdetto in parole («Stima poco affidabile oggi»), «In breve», «Come muoverti», una riga per orizzonte con la fascia «da A1 a sfidante» e il confronto col «normale» (es. «da 3% a 11%, da 0,6× a 2,1× il normale»), i cinque controlli spiegati (cosa misurano e cosa fare se accesi) e «Come leggere questi numeri». Nessun cambio di regole: stessi segnali e soglie. `data/affidabilita.json` ha il nuovo campo `orizzonti`.
- **Integrità del diario**: `journal3.verifica_estrema()` (rilegge il CSV senza pandas e ricostruisce la catena da GENESIS) → `(True, N, None)` o `(False, riga, "prev_hash non corrisponde" | "hash non corrisponde")` (riga = numero di riga nel file, intestazione = 1). `journal3.verifica()` = `(ok, n_righe, errore)`. `jobs.controllo_diario()` stampa `[diario] integrità ok: N righe, catena valida` oppure `[diario] ERRORE: catena rotta alla riga M — motivo` e fa `SystemExit(1)`; è chiamato dopo la scrittura del diario e a fine `tutto`. Il file `_h()` usa un dict, non itertuples: nessun bug da correggere.
- **Heartbeat** (`diagnostica.py`): `data/diagnostica.json` = {data_utc, ultima_previsione, giorni_da_ultima, fonti[{nome, ultima_data, giorni_ritardo, stato ok/warning/errore}]}. **I giorni sono lavorativi (lun-ven)**: sabato e domenica non contano; le festività di Wall Street non sono tolte (a Pasqua può comparire 1 giorno in più). Badge in «Salute dei dati»: verde 0-1, giallo 2-3, rosso da 4 («Diario fermo da N giorni» da 2, altrimenti «Diario aggiornato oggi»).
- **Avvisi**: da 3 giorni con `NTFY_TOPIC` → ntfy priorità alta `[Armor] Diario fermo da N giorni — controlla Actions` (al massimo uno al giorno); senza ntfy → campo `alert_diario` in `data/status.json` e banner rosso in Oggi. Da 4 giorni con `GITHUB_TOKEN` → issue su Stefo818/armor «[Armor] Diario fermo da N giorni» (se ne esiste già una aperta: un commento al giorno, nessun duplicato). Il workflow serale ha `issues: write` e `GITHUB_TOKEN`. Controllo indipendente: `python -m armor diagnostica` nel workflow «Agenda del mattino» (non scrive nel repo: usa solo ntfy e issue), così avvisa anche se il workflow serale non parte.
- **Backup**: `journal3.backup_settimanale()` → `data/journal_backups/journal_v3_AAAA-SS.csv` (una per settimana ISO), ultime 12, con `indice.json` {file, n_righe, hash_ultima_riga}. Chiamato da `tutto`.
- **Fonti**: attesa esponenziale tra i tentativi (2, 4, 8 s; 3 tentativi, più dei 2 richiesti). Se il download fallisce il file esistente NON viene toccato (si scrive solo a download riuscito); `status.json` ha ora `stato`: `ok` / `ritardo` (esiste ma non aggiornata) / `mai scaricata`. Le chiavi non-serie di status.json (`alert_diario`, `alert_diario_ntfy`) sono ignorate dai report.
- Test 87 verdi (nuovi: catena ok/rotta, uscita con errore, heartbeat, avvisi, issue senza duplicati, backup settimanale, stato fonte, riquadro affidabilità). `ruff`: i file nuovi o toccati non hanno errori di tipo F/E7/E9 introdotti da questa patch; il resto del progetto ha errori di stile preesistenti (non toccati).

## Automazioni attive
- **Workflow giornaliero** (lun-ven 23:30 UTC + di riserva 04:40 UTC): scarica i dati, calcola le previsioni, **scrive il diario v3** (A1 + percorsi, una riga per data e modello, idempotente), aggiunge gli esiti scaduti, verifica la catena, registra le impronte dei protocolli (PROTOCOLLO_VERIFICA e PROTOCOLLO_VRP), fa la copia **settimanale** del diario, scrive la diagnostica e gli avvisi, ricostruisce il sito.
- **Settimanale**: backup del diario (ultime 12 settimane). **Mensile** (workflow «Convalida mensile»): verifica storica, serie in euro, valutazione modelli. **Ricerca modello** (a mano o programmata): percorsi e **esperimento VRP** in ombra.
- **Controllo del mattino** (08:00 circa, lun-ven): `armor diagnostica`; avvisa anche se il giro serale non è partito.
- **NON automatico**: login AAII (serve un account), pesi e partecipazioni Vanguard (nessun download pubblico affidabile da qui), ^VIX1Y (non esiste su Yahoo), TER (da controllare a mano sulla scheda Vanguard). Le revisioni previste dal protocollo (10 maggio 2027; decisioni dall'8 novembre 2028) sono promemoria per te: nessuna decisione viene presa da sola.
- **Verifica in 2 minuti**: GitHub → Actions → il run più recente di «Aggiornamento giornaliero Armor» è verde? Poi nell'app → Storico → «Salute dei dati»: il badge dice «Diario aggiornato oggi» (verde). Se è giallo o rosso, controlla il log del run: cerca `[diario]` e `ERR`.

## PATCH 35 (riquadro affidabilità compatto)
- Il riquadro «Quanto fidarsi della stima di oggi» è chiuso di default: titolo, badge e una frase di sintesi con freccia «Dettagli ▾»; al tocco si apre il testo completo (come muoverti, orizzonti, cinque controlli). Solo `affidabilita.html()`, nessun cambio di regole. Test 87 verdi.

## PATCH 36 (barra Assistente colorata, notizie in italiano)
- Barra «Assistente Armor» in basso: sfondo indaco (#3b4fc4) con testo bianco, uguale in chiaro e scuro (`extra13.CSS`).
- `traduzione.py`: i titoli delle notizie (e quindi il ticker nella barra) sono tradotti in italiano in `news.run()` dopo l analisi: servizi web pubblici gratuiti senza chiavi (Google Translate pubblico, poi MyMemory), cache in `data/news/traduzioni.json` (un titolo si traduce una volta; max 4000), tempo massimo 150 s. L originale resta in `title_en`; se nessun servizio risponde il titolo resta in inglese e il ciclo non si ferma (log `[traduzione] N da cache, M nuovi, K non tradotti`). Non verificato dal cloud (nessun accesso a quei servizi): provare con il workflow «Notizie e analisi». Tema, sentimento e FinBERT usano ancora l inglese (traduzione dopo l analisi). Test 89 verdi.

## PATCH 37 (prezzi in diretta, grafici 1 ora/6 ore/1 giorno, Archivio dati)
- **Perché non era in tempo reale**: GitHub aggiorna ogni ~15 minuti e Yahoo **blocca il browser** (CORS: provato dal browser integrato, `Failed to fetch`), quindi il vecchio «aggiornamento ogni 30 secondi» del grafico non poteva funzionare. L'API pubblica di **onvista.de** risponde al browser (`/api/v1/instruments/FUND/ISIN:IE00BK5BQT80/snapshot` e `INDEX/ISIN:US78378X1072/snapshot`, qualità prezzo RLT = tempo reale; il VWCE su LS Exchange/Xetra/..., l'S&P 500 come «UBS Indikation», cioè indicazione in tempo reale sull'indice, che fuori orario di Wall Street segue il futures). `livefeed.py`: la pagina li legge ogni 15 s (solo con l'app aperta e visibile; dopo 3 errori ogni 60 s), aggiorna le due carte («● in diretta») e accumula i punti in `window.LIVETICKS`; il grafico li aggiunge. **Attenzione**: l'endpoint dei grafici storici di onvista risponde 403 con rimando alle condizioni d'uso: si usa solo il `snapshot` (uso personale, 15 s). Se un giorno onvista bloccasse, il sito resta sui dati GitHub (15 minuti) senza errori.
- **Grafici 1 ora, 6 ore, 1 giorno spenti per il VWCE**: quando vinceva una sede serale (L&S, Tradegate) il prezzo arrivava senza storico (`_pts`), quindi `intraday.json` non aveva il VWCE. Ora `live.best_vwce` usa lo storico della sede Yahoo più recente più l'ultimo prezzo della sede vincente. Per VWCE e S&P 500 i tre pulsanti restano attivi (se i punti sono pochi si riempiono dal vivo). Il sito è pubblicato dal workflow «Sito Armor» (ogni 15 minuti); `intraday.json` non è nel repository (si ricrea a ogni giro).
- **Archivio dati** (nuova pagina in app): catalogo di cosa si registra (da quando, giorni, ultimo valore, «storico completo» o «solo da oggi», «a pagamento altrove»), tabella giorno per giorno (ultimi 60 giorni) con scelta del gruppo di colonne (volatilità implicita, opzioni SPY, prezzi per sede e futures, sentimento e notizie, credito e macro, modelli), CSV completo `archivio_dati.csv`. Nuove registrazioni giornaliere: `data/archive/live_daily.csv` (VWCE per sede, spread tra sedi, futures, EUR/USD; scritto dal ciclo giornaliero) e riepilogo opzioni più ricco (`archive.riepilogo`: skew put 80%, call 105%, IV a ~7 giorni e alla scadenza più lontana, contratti, volume; la catena include ora anche scadenze a ~60/90/180 giorni). Le righe già registrate hanno solo le colonne vecchie (le nuove restano vuote). Test 92 verdi.
- Non automatico/da fare: VIX1Y non disponibile; storico opzioni e revisioni utili si costruiscono solo andando avanti.

## PATCH 38 — coerenza dei dati
- Schede VIX / S&P 500 / VWCE: niente più «Ieri / Sett. fa». Ora «Il 05/11 28,18 ▼ (−9,0%)»: chiusura precedente e chiusura di una settimana prima, con la data. Con prezzo in diretta il browser ricalcola (report.paint) riferendosi all'ultima chiusura salvata; a mercato chiuso mostra la chiusura salvata (non il prezzo del fornitore) e la variazione è sempre calcolata sulle nostre chiusure, non sul «prev» del fornitore (che per il VIX era sbagliato).
- VWCE di riferimento = Lang & Schwarz TradeCenter (ls-tc.de, strumento 1045625, sessione serale fino alle 23:00, allineata agli USA). Nuova serie `vwce_ls` (data/series/vwce_ls.csv, seme da gen 2026; `sources.fetch_ls`/`parse_ls`: solo giorni feriali, niente ripetizioni da weekend/festivi, niente punto provvisorio di oggi prima delle 23:05 Berlino). `features.vwce_display()` la usa per schede, calendario e grafico, riscalando Xetra prima della prima data. I MODELLI restano su Xetra (`vwce_series`). Se L&S non risponde da Actions resta l'archivio e si ricade su Xetra (stato `vwce_ls` in status.json). NON verificato da GitHub Actions: controllare dopo il primo ciclo.
- Calendario: in ogni cella il prezzo di chiusura sotto S e V; nel dettaglio del giorno «chiusura» per S&P e VWCE e riga «Chiusure del giorno» con VIX. (mappa.build_cal: colonne 13-15.)
- Put/Call: rapporto non valido (0) se un lato non ha contratti (archive.riepilogo) e righe <=0 ignorate in lettura (semafori._arch_series): niente più «0,00 / −100%».
- Controllo automatico `python -m armor audit-dati` (audit_dati.py, anche nel ciclo giornaliero, scrive data/audit_dati.json): VIX contro data/riferimenti/vix_utente.csv, date allineate, VWCE L&S contro Xetra, valori e salti plausibili.

## PATCH 39 — grafico di confronto (Grafici)
- S&P 500 e VWCE con linea continua; linee e pulsanti degli indicatori attivi con bagliore nel proprio colore (i spenti sono attenuati).
- Zoom per selezione: trascinando con mouse o dito in orizzontale si evidenzia un periodo e si ingrandisce (barra «Zoom: … Azzera zoom»); i pulsanti Periodo azzerano lo zoom; un tocco singolo mostra il riquadro valori. (confronto.py)

## PATCH 40 — grafico «Indice Armor contro i mercati» (PIANO_ESPANSIONE.md)
- confronto.py riscritto: linee continue e senza bagliore (il bagliore resta sulle icone dei pulsanti attivi); ~50 serie in 8 gruppi (mercati in alto in base 100: S&P, VWCE, Nasdaq, MWEQ, RSP, MSCI World, STOXX 600, emergenti, DAX, FTSE MIB, Nikkei, small cap; in basso rischio Armor e 8 famiglie, volatilità, credito/tassi, valutazioni incl. Buffett indicator, materie prime e cripto, sentimento/valute, mercato). Tutte accendibili, compresi S&P e VWCE. Serie senza dati non compaiono.
- Scorrimento: tasto destro + trascina, due dita (scorri e allarga/stringi per zoom), tasti ← →, pulsanti ◀ ▶; selezione con trascinamento = zoom; «Azzera zoom».
- infobox.py (window.armorInfo): scheda al passaggio del mouse (250 ms), pressione lunga o tocco su ⓘ; testi in glossario_serie.py (60 voci, test di copertura). Valori di riferimento (ott 2008, mar 2020, ott 2022, ultimo) calcolati dai dati.
- Nuove fonti in sources.YF: btc, eth, silver, natgas, urth, stoxx600, mweq (MWEQ.DE: se Yahoo non lo trova la linea manca); Put/Call storico CBOE (`putcall_cboe`, + archivio SPY).
- previsti.py: P/E e P/S previsti S&P 500 (yfinance su ~500 titoli, 1 volta/settimana dentro `tutto`; comando `python -m armor previsti`); la storia parte dal primo giro. NON fatto: versione VWCE (partecipazioni) — rimandato.
- confronto.json ~1,7 MB (440 KB compresso da GitHub Pages).
- sw.js cache armor-v40.

## PATCH 41 — pagina «Oggi» riordinata, Semafori ridisegnati, schede delle famiglie
- Nuovo ordine di «Oggi»: 1) Indice Armor + schede VIX/Put-Call/S&P/VWCE; 2) Semafori di oggi (nuovo); 3) valutazioni P/E-P/S, prossimo evento, grafico di confronto; 4) tutto il resto (Oggi cosa faccio, affidabilità, bilancio, ciclico, mappa, calendario).
- Semafori di oggi (semafori.oggi_html): barra proporzionale ok/attenzione/allarme (tocca → elenco), una pillola per gruppo (12 gruppi dei semafori; pallini colorati per indicatore; tocca → indicatori del gruppo con valore e frase), riga «Cambiati da <data>» da data/semafori_storia.csv (scritto a ogni build, idempotente per data; parte da oggi, il confronto compare dal giorno dopo).
- Mappa settimanale e pagina Indici: ogni intestazione ha la scheda (ⓘ, mouse fermo, pressione lunga): cosa misura, cosa comprende (lista indicatori e peso della famiglia da armor_index.GROUPS), come leggere i numeri, valori a dic 2007 / mar 2020 / ott 2022 / oggi; ogni indicatore: cosa misura, quando preoccuparsi, soglie, famiglia. Testi in mappa.FAM_INFO / ROW_INFO.
- Termometro Indice Armor: «Il 05/11 …» con le date reali (non più «Ieri»). Il riquadro dei 3 orizzonti (finestra Armor) usa ancora «Ieri / Sett. fa».
- Archivio opzioni SPY: la data è quella dell'ultima seduta USA chiusa; le righe salvate di sabato/domenica sono ricondotte al venerdì (archive.venerdi_se_weekend, anche in lettura).
- Pulizia ruff (F) in cruscotto.py. sw.js cache armor-v41.

## PATCH 42 — Notizie
- Nuova pagina «Notizie» (menu, dopo Oggi): novita.py; archivio degli ultimi 30 giorni dai file data/news/AAAA-MM-GG.json (deduplicato per titolo, ordine dal più recente), diviso per giorno (Oggi / Ieri / data), filtri (Tutte, Macro e Fed, Mercati, Aziende di VWCE, Settori e temi, Solo negative/positive), ricerca testuale, titolo in italiano con l'originale sotto, link, tono, fonte, temi. Dati in series/notizie.json (a richiesta) o incorporati nel file locale.
- Assistente: nuova scheda «Notizie» (le 12 più importanti + pulsante «Apri tutte le notizie»). Toccando il testo di una notizia nella barra in basso si apre l'Assistente sulla scheda Notizie (toccando il resto della barra, come prima).
- Barra in basso: cambio ogni 9 s (era 5), dissolvenza 400 ms, ferma con mouse o dito sopra (riparte dopo 3 s); notizie dalla più recente alla meno recente con data breve («oggi 14:20», «ven 06/11 17:00»), dopo indice ed eventi; window.TICKER ora è una lista di {t, n}.
- Nota: «divise per giorni» nella barra = data breve davanti a ogni notizia; la pagina Notizie ha le intestazioni di giorno.
- sw.js cache armor-v42.
