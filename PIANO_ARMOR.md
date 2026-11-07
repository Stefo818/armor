# PIANO ARMOR — come renderla davvero efficace

Documento di lavoro per Sonnet (e per l'utente). Si esegue **una fase alla volta**, nell'ordine.
Ogni compito ha: file da toccare, cosa fare, criterio di accettazione, test. Non si passa al compito successivo se il criterio non è soddisfatto.

---

## 0. Regole fisse (Sonnet le rispetta sempre)

- **Lingua**: tutto in italiano, testi semplici. Istruzioni all'utente a blocchi brevi con il luogo: [PowerShell], [Chrome], [Telefono]. Comandi sempre scritti per intero.
- **Python 3.11** (GitHub Actions). Mai f-string annidate con le stesse virgolette (`f"{f"{x}"}"`): su 3.11 è un SyntaxError. Prima di consegnare: `python3.11 -m compileall -q src tests` e `python3 -m pytest -q tests`.
- **Niente rete nel container**: Yahoo, FRED, CFTC, ntfy non si possono provare qui. Ogni funzione di rete deve avere una funzione "pura" testabile con dati finti (fixture) e un `try/except` che non blocca il resto.
- **Nessuno sguardo al futuro**: ogni variabile usata per prevedere il giorno t deve essere nota la sera del giorno t (dati mensili/settimanali spostati del loro ritardo di pubblicazione). Ogni nuova variabile ha un test "no lookahead".
- **Onestà**: se un modello non batte la frequenza storica ("normale"), l'app lo dice e mostra il normale. Mai numeri inventati, mai "previsioni certe".
- **Consegna**: patch zip con solo i file cambiati (mai `data/live.json`, `data/intraday.json`, `data/news/*`, `data/reports/*`, `data/registry/*`, `sentiment.xls`, `site/`) → `D:\Armor\patchN.zip` → estrazione → istruzioni: [PowerShell] `cd D:\Armor; Remove-Item patchN.zip; git add .; git commit -m "..."; git push` → [Chrome] Actions: Aggiornamento giornaliero → Notizie e analisi → Sito Armor.
- **Tempo**: il workflow giornaliero deve restare sotto 15 minuti; i calcoli pesanti (backtest) vanno solo nella Convalida mensile (`valida.yml`, limite 45 min).
- Alla fine di ogni fase aggiornare `CONTINUA_DA_QUI.md` (stato, cosa manca, numeri di verifica).

---

## 1. Diagnosi onesta (stato a novembre 2026)

| Parte | Stato | Numeri |
|---|---|---|
| Modello cali A1 (logistica, 8 variabili di prezzo S&P dal 1928) | buono a breve | AUC ≈ 0,76 a 10 giorni e 1 mese |
| Stesso modello a 3 e 6 mesi | **non funziona** | AUC ≈ 0,43 / 0,42 (peggio del caso) |
| Probabilità di rialzo | calcolate a parte (matrice), non verificate dal vivo | — |
| Volatilità (HAR + VIX) | buona | errore 4,4 contro 5,5 della semplice persistenza |
| Indice Armor 1–100 | utile | AUC 0,72 (calo ≥10% a 3 mesi), 0,84 (volatilità alta) |
| Dati | fragili | FRED da CSV spesso irraggiungibile da GitHub; Yahoo rallenta |
| Apprendimento dal vivo | appena avviato | poche previsioni scadute |

**Conclusione**: la direzione del mercato a 3–6 mesi non è prevedibile in modo affidabile con nessun modello noto. Si può invece prevedere bene **quanto sarà agitato il mercato** e quindi **la probabilità di cali e rialzi grandi nel breve**. Obiettivo realistico di "previsioni efficaci":

1. probabilità **calibrate** (quando Armor dice 20%, succede circa 2 volte su 10);
2. **mai peggio del normale** su nessun orizzonte (se non c'è abilità, si mostra il normale);
3. calo, rialzo e scenari **coerenti tra loro** (stesso motore, somme giuste);
4. verifica continua sui dati reali.

---

## FASE 0 — Stabilità dei dati (prima di tutto)

### 0.1 FRED con chiave API (gratuita)
- **Utente**: [Chrome] crea la chiave su https://fred.stlouisfed.org/docs/api/api_key.html → [Chrome] GitHub → repo armor → Settings → Secrets and variables → Actions → New repository secret: nome `FRED_API_KEY`.
- **File**: `src/armor/sources.py`, `.github/workflows/daily.yml`, `valida.yml`, `notizie.yml` (aggiungere `FRED_API_KEY: ${{ secrets.FRED_API_KEY }}` in `env`).
- **Cosa fare**: `fetch_fred(code)` usa prima `https://api.stlouisfed.org/fred/series/observations?series_id=CODE&api_key=KEY&file_type=json&observation_start=AAAA-MM-GG` (solo gli ultimi 3 anni se la serie esiste già), poi ripiega sul CSV attuale. Separare il parsing in `parse_fred_json(text)` (testabile).
- **Accettazione**: test con JSON finto; con chiave assente il comportamento è identico a oggi.

### 0.2 Prezzi S&P con riserva (Stooq)
- **File**: `sources.py`.
- **Cosa fare**: se Yahoo fallisce per `sp500`, `vix`, `ndx`, scaricare il CSV gratuito Stooq (`https://stooq.com/q/d/l/?s=^spx&i=d`, `^ndx`; il VIX non c'è su Stooq: in quel caso si usa FRED `VIXCLS`). Funzione pura `parse_stooq_csv`.
- **Accettazione**: test con CSV finto; `status.json` indica la fonte usata.

### 0.3 Stato delle fonti visibile
- **File**: `report.py` (pagina Storico), `bilancio.py`.
- **Cosa fare**: tabella "Salute dei dati": per ogni serie importante data dell'ultimo valore, fonte, giorni di ritardo, semaforo (verde ≤ ritardo atteso, giallo ≤ 2×, rosso oltre). Nel bilancio serale una riga se una serie chiave è rossa.
- **Accettazione**: con una serie vecchia di 30 giorni la riga è rossa.

### 0.4 Registro completo e controllato
- **File**: `registry.py`, `jobs.py`.
- **Cosa fare**: verificare che ogni giorno il registro salvi: tutte le serie usate dai modelli, probabilità di calo **e** rialzo per tutte le soglie (non solo la principale), Indice Armor e famiglie, scenari a 3 mesi, versione del modello. Aggiungere `registry.check()` che stampa `[registro] colonne mancanti: ...`.
- **Accettazione**: test che `row_for` contiene le chiavi attese.

---

## FASE 1 — Il motore delle previsioni (la parte che conta)

Idea: **tre motori diversi + combinazione verificata + ritorno al normale quando non c'è abilità**.

### 1.1 Motore "simulazione storica filtrata" (FHS) — nuovo, il più importante
Perché: la volatilità è prevedibile; da una buona previsione di volatilità si ricavano in modo coerente **tutte** le probabilità (cali e rialzi a ogni soglia, scenari, intervalli).
- **File nuovo**: `src/armor/fhs.py`. Dipendenza: `arch` (aggiungere a `requirements.txt`).
- **Cosa fare**:
  1. rendimenti logaritmici giornalieri S&P; modello GJR-GARCH(1,1) con distribuzione t (`arch_model(r*100, vol="GARCH", p=1, o=1, q=1, dist="t")`);
  2. residui standardizzati z = r/σ (tutta la storia);
  3. per oggi: 5.000 percorsi di 126 sedute; la varianza segue la ricorsione GJR, gli shock si pescano a caso dai z storici (bootstrap); deriva = 0 oppure media storica (scegliere con il backtest);
  4. opzionale: scalare σ del primo mese verso il VIX (σ_imp = VIX/√252) con peso scelto nel backtest;
  5. per ogni percorso: calo massimo, rialzo massimo, rendimento finale a 10/21/63/126 sedute → probabilità per tutte le soglie `THRESHOLDS`, i 5 scenari (`outlook.SCEN_EDGES`), quantili 10/50/90.
  - Funzione `forecast(p, date=None, n=5000, seed=0) -> dict` con la stessa struttura di `outlook.probability_matrix` (chiavi `down`, `up`, `ret_analog`…), così il resto dell'app la usa senza modifiche.
  - Vettorizzare con numpy (niente cicli Python per percorso). Tempo giornaliero < 10 s.
- **Backtest** (solo mensile): `fhs.backtest(start="1990-01-01", step=21)`: rifit ogni 252 sedute, previsione con dati fino a t, confronto con l'esito reale. Salva `data/fhs_eval.csv`.
- **Accettazione**: test su serie finta (es. rumore con volatilità a salti) che le probabilità aumentano quando la volatilità sale; somma degli scenari = 1; calo ≥X% decrescente in X.

### 1.2 Modello multi-variabile (dal 1990)
- **File**: `model.py` (o nuovo `model_mv.py`), `challenger.py`.
- **Cosa fare**: stesso schema del modello attuale ma con variabili aggiuntive allineate senza sguardo al futuro: VIX, VIX3M/VIX, VIX − volatilità realizzata (premio per il rischio), variazione a 1 mese dello spread BAA e HY, curva 10Y−3M, NFCI, ampiezza (se storia sufficiente), punteggi delle 8 famiglie dell'Indice Armor. Due algoritmi: logistica regolarizzata e `HistGradientBoostingClassifier` (con `monotonic_cst` dove il segno è noto: VIX ↑ ⇒ rischio ↑).
- **Accettazione**: test "no lookahead" per ogni variabile nuova.

### 1.3 Validazione corretta (purged walk-forward)
- **File**: `validate.py`, `challenger.py`.
- **Cosa fare**: i bersagli a 3–6 mesi si sovrappongono; nella validazione escludere dal training gli ultimi h giorni prima di ogni data di prova (purge) più un margine di 5 sedute (embargo). Metriche per orizzonte e soglia principale: Brier, log loss, BSS contro il normale, AUC, tabella di taratura a 10 gruppi. Intervalli di confidenza con **bootstrap a blocchi** (blocchi di 63 sedute).
- **Accettazione**: `python -m armor valuta-modelli` produce `data/model_eval.json` con questi numeri per: A1, FHS, multi-variabile logit, multi-variabile GBM.

### 1.4 Combinazione e taratura
- **File nuovo**: `src/armor/ensemble.py`.
- **Cosa fare**:
  1. per ogni orizzonte, pesi non negativi (somma 1) tra i motori che minimizzano il log loss **fuori campione** (usare le previsioni walk-forward di 1.3, mai quelle in campione);
  2. taratura finale con regressione isotonica sulle previsioni fuori campione combinate;
  3. **ritorno al normale in base all'abilità**: `p_finale = base + w·(p_combinata − base)`, con `w = clip(BSS_mobile_5anni / 0,10, 0, 1)`. Se l'abilità è nulla o negativa, si mostra il normale e l'app lo dice ("a 6 mesi nessun modello batte la media storica: mostro la media").
  4. coerenza: P(calo ≥ 10%) ≤ P(calo ≥ 5%) ecc. (ordinare/monotonizzare dopo la combinazione).
- **Regola di adozione (fissata in anticipo)**: il nuovo motore combinato sostituisce A1 solo se migliora il BSS su almeno 2 orizzonti sia nel 2000–2012 sia dal 2013, e non peggiora nessun orizzonte di oltre 0,01. Altrimenti resta A1 e si registra il tentativo in `data/models.json`.
- **Accettazione**: sui dati storici il BSS del combinato a 3 e 6 mesi è ≥ 0 (grazie al ritorno al normale) e a 10 giorni/1 mese ≥ quello di A1.

### 1.5 Scenari e intervalli coerenti
- **File**: `chiaro.py`, `outlook.py`, `report.py`.
- **Cosa fare**: barre calo/rialzo, scenari a 5 casi e "caso brutto/tipico/buono" presi **tutti dallo stesso motore combinato**. Intervalli all'80% verificati con conformal prediction semplice (allargare/stringere i quantili finché, fuori campione, la copertura è 80% ± 3%).
- **Accettazione**: copertura misurata mostrata nella pagina Previsioni.

### 1.6 Spiegazione di ogni previsione
- **Cosa fare**: per la logistica contributo = coefficiente × valore standardizzato; per FHS "volatilità attesa X% contro normale Y%"; per GBM importanza per permutazione sugli ultimi 5 anni. Nel riquadro "Perché?" le prime 3 cause in parole semplici.

---

## FASE 2 — Indice Armor più utile

### 2.1 Dall'indice alla probabilità
- **File**: `armor_index.py`.
- **Cosa fare**: regressione isotonica storica (solo indice del giorno prima) tra indice e: calo ≥5% a 1 mese, calo ≥10% a 3 mesi, volatilità > 25%. Nel riquadro: "Con un indice a 52, in passato un calo ≥10% entro 3 mesi è arrivato nel X% dei casi (normale 15%)".

### 2.2 Pesi delle famiglie verificati
- **Cosa fare**: confrontare i pesi fissi con pesi stimati (logistica con coefficienti ≥ 0 sulle 8 famiglie, fit solo fino al 2012, prova dal 2013). Adottare i pesi stimati solo se l'AUC dal 2013 migliora di almeno 0,02 su 2 eventi su 3. Mai riottimizzare più di una volta l'anno.

### 2.3 Indice come variabile del modello
- Le 8 famiglie entrano nel modello multi-variabile (1.2): l'indice diventa anche un ingrediente delle previsioni, non solo un indicatore.

### 2.4 Verifica dal vivo
- **File**: `learning.py`.
- **Cosa fare**: ogni giorno, per i giorni con esito ormai noto, AUC dal vivo dell'indice (quando ci sono almeno 40 esiti con evento) e tabella per fascia. Mostrarla in Storico.

---

## FASE 3 — App straordinaria (chiarezza prima di tutto)

### 3.1 Pagina "Oggi" in 5 blocchi, niente di più
1. Oggi cosa faccio (una frase);
2. Indice Armor + termometro + probabilità corrispondente;
3. Calo o rialzo (barre per periodo + "Perché?");
4. P/E e P/S di VWCE, S&P 500, Nasdaq;
5. Prossimo evento importante.
Tutto il resto nelle altre pagine o nella finestra Assistente.

### 3.2 Pagina "Quanto mi posso fidare"
- Grafico di taratura (previsto contro reale, a 10 gruppi) per ogni orizzonte, dal backtest e dal vivo; BSS con intervallo; frase semplice: "a 1 mese Armor batte la media storica; a 6 mesi no".

### 3.3 Velocità
- `data.json` diviso per serie (`data/<chiave>.json`) caricato solo quando si apre un grafico; sezioni pesanti (scenari per indicatore, mappa mensile, crisi) caricate all'apertura. Obiettivo: pagina iniziale < 150 KB.

### 3.4 Notifiche che servono
- Solo quando cambia qualcosa: fascia dell'Indice Armor, divergenza attivata, evento importante domani, previsione 1 mese passata da "normale" a "elevato". Massimo 1 notifica al giorno (più gli allarmi personali).

### 3.5 Il mio PAC
- Campo nell'app (localStorage): importo mensile e data di inizio → valore stimato del PAC, prezzo medio di carico, effetto dei cali ("questo calo ti fa comprare quote a −8% rispetto al prezzo medio"). Nessun consiglio di vendita.

---

## FASE 4 — Imparare davvero dai dati reali

### 4.1 Modalità ombra
- Ogni giorno anche i motori sfidanti (FHS, multi-variabile, combinato) scrivono la loro previsione in `data/journal_shadow.csv` (stessa catena di firme). Dopo 6 mesi si confrontano dal vivo con il modello in uso.

### 4.2 Taratura dal vivo
- Quando per un orizzonte ci sono almeno 250 previsioni scadute (dati sovrapposti: contano come circa 250/h campioni indipendenti, dirlo), applicare una correzione di taratura stimata sui dati reali, solo se migliora il Brier fuori campione (validazione su metà dei casi più recenti).

### 4.3 Notizie come variabile (più avanti)
- Il tono delle notizie (FinBERT) entra nei modelli **solo** dopo almeno 18 mesi di storia giornaliera salvata e solo se supera la regola di adozione. Fino ad allora resta informativo.

### 4.4 Rapporto mensile automatico
- Nel bilancio del 1° del mese: cosa ha previsto Armor, cosa è successo, se il modello è cambiato e perché (da `models.json` e `learning.csv`).

---

## Cose da NON fare
- Non aggiungere variabili "perché sembrano buone" senza la regola di adozione.
- Non ottimizzare pesi o soglie guardando i risultati dal 2013 (quello è il periodo di prova).
- Non mostrare previsioni a 3–6 mesi più sicure di quanto il backtest giustifichi.
- Non mettere calcoli pesanti nel workflow giornaliero.
- Non cancellare dati storici o il diario delle previsioni.

---

## Prompt pronti per Sonnet (uno per sessione)

Ogni prompt va incollato in una **conversazione nuova** di Claude (Cowork) collegata al PC con la cartella `D:\Armor`.

**Fase 0**
> Lavori sul progetto Armor in D:\Armor. Leggi prima D:\Armor\PIANO_ARMOR.md (sezione 0 e FASE 0) e, se esiste, D:\Armor\CONTINUA_DA_QUI.md. Esegui i compiti 0.1, 0.2, 0.3, 0.4 rispettando le regole della sezione 0: compatibilità Python 3.11, test con dati finti, nessun calcolo pesante nel giornaliero. Lavora su una copia nel cloud, verifica con `python3.11 -m compileall -q src tests` e `python3 -m pytest -q tests`, consegna una patch zip in D:\Armor, estraila e dammi le istruzioni [PowerShell]/[Chrome] per commit, push e avvio dei workflow. Aggiorna CONTINUA_DA_QUI.md. Rispondi in italiano, istruzioni brevi a blocchi.

**Fase 1 (dividerla in due sessioni)**
> Progetto Armor in D:\Armor. Leggi D:\Armor\PIANO_ARMOR.md (sezione 0 e FASE 1) e D:\Armor\CONTINUA_DA_QUI.md. In questa sessione esegui solo 1.1 (motore FHS con backtest mensile) e 1.3 (validazione purged walk-forward e comando `valuta-modelli`). Usa i dati già presenti in D:\Armor\data per il backtest locale e riportami i numeri (Brier, BSS, AUC per orizzonte) di A1 e FHS. Non cambiare ancora il modello in uso. Consegna la patch come descritto nella sezione 0 e aggiorna CONTINUA_DA_QUI.md.

> Progetto Armor in D:\Armor. Leggi D:\Armor\PIANO_ARMOR.md (sezione 0 e FASE 1) e D:\Armor\CONTINUA_DA_QUI.md. Esegui 1.2, 1.4, 1.5, 1.6. Applica la regola di adozione scritta in 1.4: adotta il motore combinato solo se la supera, altrimenti registra il tentativo e lascia A1. Mostrami la tabella finale dei numeri. Consegna la patch e aggiorna CONTINUA_DA_QUI.md.

**Fase 2**
> Progetto Armor in D:\Armor. Leggi D:\Armor\PIANO_ARMOR.md (sezione 0 e FASE 2) e D:\Armor\CONTINUA_DA_QUI.md. Esegui 2.1, 2.2, 2.3, 2.4 con le regole indicate. Consegna la patch e aggiorna CONTINUA_DA_QUI.md.

**Fase 3**
> Progetto Armor in D:\Armor. Leggi D:\Armor\PIANO_ARMOR.md (sezione 0 e FASE 3) e D:\Armor\CONTINUA_DA_QUI.md. Esegui 3.1–3.5. Prima di consegnare fai screenshot della pagina con Playwright a larghezza telefono (430 px) e controlla che non ci siano errori JavaScript. Consegna la patch e aggiorna CONTINUA_DA_QUI.md.

**Fase 4**
> Progetto Armor in D:\Armor. Leggi D:\Armor\PIANO_ARMOR.md (sezione 0 e FASE 4) e D:\Armor\CONTINUA_DA_QUI.md. Esegui 4.1, 4.2 (con le soglie indicate), 4.4; per 4.3 prepara solo il codice disattivato. Consegna la patch e aggiorna CONTINUA_DA_QUI.md.

---

## In sintesi
- **Fase 0** rende i dati affidabili (FRED con chiave, Stooq di riserva, salute dei dati visibile).
- **Fase 1** è il salto di qualità delle previsioni: un motore di simulazione basato sulla volatilità, un modello con più variabili, una validazione corretta e una combinazione che non è mai peggio del normale.
- **Fase 2** trasforma l'Indice Armor in probabilità verificate.
- **Fase 3** rende l'app chiara e veloce.
- **Fase 4** fa imparare Armor dai risultati reali, con regole fisse e senza illusioni.
