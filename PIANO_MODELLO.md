# PIANO MODELLO — migliorare davvero le previsioni di Armor

Documento di lavoro per l'agente che sviluppa Armor. Va letto per intero prima di scrivere codice, insieme a `CONTINUA_DA_QUI.md`.
L'obiettivo è fare tutto il possibile per migliorare il modello: aggiungere la salute delle aziende e ogni dato utile e gratuito,
allungare la storia su cui si impara, e provare modelli migliori. Però conta solo quello che regge una verifica fuori campione.
Un miglioramento che c'è solo nei dati di addestramento è un'illusione, e va scartato e dichiarato.

---

## 0. Regole fisse del progetto (non cambiarle)

- App personale in italiano su VWCE (PAC mensile). Sito statico GitHub Pages (repo `Stefo818/armor`), PWA. Calcoli in GitHub Actions (Python 3.11: niente f-string annidate con lo stesso tipo di virgolette). Nessuna AI a pagamento. Non è consulenza finanziaria.
- Copia di lavoro: `/home/claude/armor_work/Armor`. Se manca (sessione nuova): [device_bash] `cd $HOME/mnt/Armor && python3 scripts/copia_cloud.py` → `device_stage_files` di `D:\Armor\scratch\repo.zip` → estrai in `/home/claude/armor_work/Armor`. Solo i dati aggiornati: `python3 scripts/copia_cloud.py serie` → `D:\Armor\scratch\series.zip` → estrai sopra la copia di lavoro.
- Test: `python3.11 -m compileall -q src tests` e `python3 -m pytest -q tests`. Sito: `PYTHONPATH=src python3 -m armor sito`. Prima di consegnare UI: screenshot Playwright a 430px (servire `site/` con `python3 -m http.server 8766`), zero errori in console.
- Consegna: `patchN.zip` solo con i file cambiati. Mai includere: `data/live.json`, `data/intraday.json`, `data/news/*`, `data/reports/*`, `data/registry/*`, `data/series/*`, `sentiment.xls`, `site/`, `data/models.json`. Copia in `/mnt/user-data/outputs`, `SendUserFile`, `device_commit_files` in `D:\Armor\patchN.zip`, estrai con `device_bash` (python zipfile) in `$HOME/mnt/Armor`.
- Risposta all'utente: in italiano, breve, a blocchi con il luogo di ogni passo e i comandi per intero:
  [PowerShell] `cd D:\Armor; Remove-Item patchN.zip; git add .; git commit -m "..."; git push` (se il push viene rifiutato: `git pull --no-rebase; git push`)
  [Chrome] GitHub → Actions → lanciare i workflow indicati e aspettare il verde
  [Telefono] ricaricare l'app due volte.
  Chiedere le righe `[dati]`/`[ombra]`/`ERR` se qualcosa non va.
- Aggiornare `CONTINUA_DA_QUI.md` a ogni fase (sezione "PATCH N").
- Risparmio di token: non leggere file grandi per intero (`report.py`, `extra13.py`, `mappa.py`): usa grep e leggi solo le righe utili. Raggruppa i controlli in un solo script in scratch invece di molti comandi separati. Riusa le funzioni esistenti.
- Limiti di rete: il container cloud e il PC dell'utente NON raggiungono FRED/Yahoo/multpl (proxy 403). Sul PC non c'è sklearn. I download avvengono solo in GitHub Actions. Dopo che Actions ha scaricato, l'utente fa `git pull`. Poi l'agente esegue `python3 scripts/copia_cloud.py serie` con `device_bash`, carica `D:\Armor\scratch\series.zip` con `device_stage_files` e lavora nel cloud, dove sklearn c'è.
  Acceleratore facoltativo: se l'utente ha un piano individuale a pagamento, può consentire i domini in claude.ai → Impostazioni → Capabilities. In quel caso l'agente può scaricare direttamente.

---

## 1. Punto di partenza (misurato, novembre 2026)

- Indice Armor: per i cali ≥10% entro 3 mesi l'AUC è 0,72 (verifica giornaliera, `data/armor_index_eval.json`). Per i mesi molto volatili è 0,84. È l'abilità vera dell'app e va preservata.
- Direzione su/giù: nessuna variabile e nessun modello (logistica, gradient boosting) batte la frequenza storica, né a 1, 3, 6 o 12 mesi (BSS ≤ 0). A 12 mesi i fondamentali sono addirittura invertiti (AUC 0,2–0,48): i dati peggiori arrivano vicino ai minimi.
- Fondamentali e macro (utili, CAPE, premio utili-bond, credito, sussidi, curva), in walk-forward mensile 2003–2026 per i cali ≥10%:

  | Orizzonte | AUC fondamentali | AUC Armor da solo |
  |---|---|---|
  | 3 mesi | 0,70 | 0,67 (mensile) |
  | 6 mesi | 0,66 | 0,58 |
  | 12 mesi | 0,63 | 0,51 |

  Però il BSS è negativo: le probabilità sono mal tarate, perché i fondamentali danno "rischio alto" troppo spesso e troppo a lungo. Il gradient boosting fa peggio della logistica: è sovradattamento.
- Segnali singoli dal 1990. Probabilità di un calo ≥10% entro 6 mesi, con segnale acceso contro spento:

  | Segnale | Acceso | Spento |
  |---|---|---|
  | Utili <−10% annuo | 44% | 17% |
  | Prezzo sotto la media a 10 mesi | 44% | 15% |
  | CAPE > 30 | 38% | 16% |
  | Curva invertita (ultimi 12 mesi) | 37% | 17% |
  | Sussidi +20% dal minimo | 37% | 20% |
  | Spread +0,5 punti in 6 mesi | 32% | 21% |
  | VIX > 30 | 30% | 21% (ma +21,8% a 12 mesi) |

- Cause del limite:
  - pochi eventi: dal 2000 ci sono 6–7 grandi cali;
  - i prezzi anticipano gli utili di 6–9 mesi;
  - i segnali pubblici sono già nei prezzi;
  - le valutazioni restano alte per anni.
- Script di questa analisi: `D:\Armor\scratch\ricerca_opus\` (`fund.py`, `cond.py`, `combo.py`). Partire da lì.

Le leve vere, in ordine di valore atteso:
- (a) Allungare la storia mensile al 1927–1950 per avere 20–25 grandi cali invece di 6–7.
- (b) Aggiungere i dati di salute aziendale e di credito che mancano.
- (c) Un modello a due stadi: prima la probabilità di recessione, poi il rischio di calo.
- (d) Gli analoghi storici, per dare una tendenza precisa e onesta.
- (e) Una taratura corretta.

---

## 2. Regole anti-illusione (obbligatorie)

1. Solo walk-forward: ogni anno di prova usa solo dati precedenti, con un buco pari all'orizzonte più il ritardo di pubblicazione (purge + embargo). Mai standardizzare o scegliere soglie usando il periodo di prova.
2. Ritardi di pubblicazione: ogni serie entra solo dalla data in cui era nota (tabella in §3). I dati macro FRED sono rivisti. Si preferiscono serie non rivisionate (mercato, sussidi, sondaggi); per le altre si applica un ritardo prudente. Facoltativo: usare ALFRED (`realtime_start`) con `FRED_API_KEY` per UNRATE, PAYEMS, INDPRO.
3. Pre-registrazione: le soglie dei segnali singoli sono fissate prima del test (quelle di §1 e dei semafori), non ottimizzate.
4. Registro di ogni prova in `data/ricerca/registro_prove.csv`: data, modello, variabili, obiettivo, orizzonte, periodo, AUC, BSS, numero di eventi. Il numero totale di prove va mostrato in Fiducia. Più prove fai, più alto deve essere il miglioramento richiesto.
5. Hold-out: gli anni 2019–2026 (con gli eventi 2020, 2022 e 2025) si usano una sola volta, alla fine, per la decisione di adozione. Prima si lavora su 1960–2018 (storia lunga) e su 2000–2018.
6. Stabilità: un miglioramento conta solo se c'è in almeno 2 di 3 sottoperiodi (1960–1989, 1990–2009, 2010–2018) e in nessuno peggiora oltre 0,02 di AUC.
7. Semplicità: al massimo circa 12 variabili per modello. Variabili trasformate (variazioni, z-score su 10 anni passati). Il gradient boosting solo con `monotonic_cst`, `max_depth=2` e `min_samples_leaf` grande. Se non batte la logistica in tutti i sottoperiodi, si tiene la logistica.
8. Analisi per episodio: per ogni grande calo, quanti mesi prima il modello era in allarme e quanti mesi di falso allarme ha dato. Questo va mostrato all'utente.
9. Esito negativo = esito valido: se qualcosa non migliora, si scrive e si mostra. Mai presentare come previsione ciò che non ha superato le regole.

---

## 3. Dati da aggiungere (Fase A)

Aggiungere i codici a `FRED` in `src/armor/sources.py`. Le serie fallite sono già gestite da `update_all`, che le salta. Verifica ogni codice una volta: se non esiste, toglilo e annotalo. Le serie trimestrali o mensili si scaricano al massimo una volta a settimana, per tenere il giornaliero sotto i 15 minuti. Le derivate vanno in un nuovo modulo `src/armor/fondamentali.py`.

Già presenti in `data/series` sul PC (verificare): `cpi, indpro, payems, unrate, retail, umcsent, neworder, dgorder, philly, empire, walcl, tga, rrp, wresbal, fedfunds, be10y, gdp, equity_value, ig_oas, hy_oas (solo dal 2023), breadth200, breadth50, nh_nl, pput, cot_*, gpr*, fear_greed, top_fcf_yield, top_pe, top_ps, ai_capex_ocf, rsp, spy, eem, sec_*`.

**Salute delle aziende**

| id | Fonte / codice | Frequenza | Ritardo | Uso |
|---|---|---|---|---|
| eps_sp | derivata: sp500 mensile / pe_m | mensile | 150 gg (patch 21: con 60 gg parte dell'abilità era sguardo al futuro) | `eps_g3`, `eps_g12` (crescita utili) |
| sales_sp | derivata: sp500 / ps_m (dal 2000) | trimestrale | 90 gg | `sales_g12`, margine = eps/sales |
| earn_shiller, div_shiller | estendere `fetch_shiller()` (colonne E, D, CPI, GS10 del file ie_data.xls) | mensile dal 1871 | 120 gg | utili lunghi per la storia lunga |
| cp | FRED `CP` (profitti dopo le tasse) | trimestrale | 90 gg | `cp_g4`, `cp/gdp` |
| delinq_biz | FRED `DRBLACBS` (ritardi prestiti alle imprese) | trimestrale | 75 gg | sofferenza aziende |
| chargeoff_biz | FRED `CORBLACBS` (prestiti alle imprese cancellati) | trimestrale | 75 gg | insolvenze |
| delinq_cc | FRED `DRCCLACBS` (carte di credito) | trimestrale | 75 gg | sofferenza delle famiglie |
| busloans | FRED `BUSLOANS` (prestiti a imprese) | mensile | 30 gg | contrazione del credito (var. 6 mesi) |
| rev_breadth | yfinance `Ticker.eps_revisions` sui 30 titoli maggiori (`news.TOP20` + altri) | giornaliera da oggi | 1 | (rialzi − ribassi a 30 gg)/totale; solo monitorata finché lo storico è sotto 2 anni |
| fwd_growth | yfinance `Ticker.earnings_estimate` (crescita attesa anno in corso/prossimo), pesata per capitalizzazione | giornaliera da oggi | 1 | come sopra |

**Inflazione e politica monetaria**: `CPILFESL` (core CPI), `PCEPILFE` (core PCE), `T5YIFR` (inflazione attesa 5y5y). Derivate: `cpi_yoy`, `core_yoy`, tasso Fed reale = `fedfunds − core_yoy`, accelerazione dell'inflazione (variazione a 6 mesi del tasso annuo). Ritardo 20 gg.

**Economia reale e recessione**:
- `CFNAI` (30 gg), `SAHMREALTIME` (10 gg), `CCSA` (sussidi continuativi, 10 gg), `PERMIT` (30 gg), `ISRATIO` (scorte/vendite, 45 gg).
- `USREC` serve solo come etichetta per il modello a due stadi. Le recessioni NBER sono annunciate con circa 12 mesi di ritardo, quindi purge di 24 mesi.
- `RECPROUSM156N` solo come contesto: è rivista, quindi mai usarla come variabile di addestramento.

**Liquidità**:
- Liquidità netta Fed = `walcl − tga − rrp`: controllare le unità (WALCL in milioni, RRPONTSYD in miliardi).
- Variazione a 13 settimane della liquidità netta.
- `M2SL` (var. annua, 30 gg).
- Sottoindici NFCI: `NFCICREDIT`, `NFCILEVERAGE`, `NFCIRISK`.
- `KCFSI` (stress, Kansas City).

**Leva ed euforia**: margin debt FINRA, mensile, file Excel dalla pagina "Margin Statistics" di finra.org (trovare il link attuale con un solo tentativo; se non c'è, rinunciare e annotarlo). Variabile: var. annua del margin debt (picchi di leva prima dei massimi). Ritardo 30 gg.

**Mercato interno** (Yahoo, giornaliero; aggiungere a `YF` in `sources.py`): `IWM`, `SMH`, `IYT`, `KRE`, `HG=F` (rame). Rapporti:
- `IWM/SPY` (piccole/grandi);
- `RSP/SPY` (equal-weight/cap-weight: concentrazione sui giganti);
- `sec_xly/sec_xlp` (ciclici/difensivi);
- `SMH/SPY`, `IYT/SPY`, `KRE/SPY`;
- rame/oro;
- `HYG/IEF` (appetito per il rischio di credito: sostituto storico di `hy_oas`, che su FRED parte solo dal 2023).

Per ogni rapporto: variazione a 3 e 6 mesi e distanza dalla media a 200 giorni.

**Europa e globale** (VWCE è globale):
- ECB CISS (stress sistemico area euro): `https://data-api.ecb.europa.eu/service/data/CISS/D.U2.Z0Z.4F.EC.SS_CIN.IDX?format=csvdata` (verificare la chiave).
- `EEM/VT`, `stoxx50`, `eurusd` già presenti.
- OECD CLI facoltativo (API SDMX OECD; un solo tentativo).

**Storia lunga mensile** (la leva più importante):
- FRED `BAA` e `AAA` (dal 1919): spread BAA − titoli di Stato lunghi;
- `GS10` (dal 1953);
- `TB3MS` (dal 1934): curva lunga 10a − 3m;
- `CPIAUCNS` (dal 1913);
- `INDPRO` (dal 1919);
- `UNRATE` (dal 1948);
- `PAYEMS` (dal 1939);
- Shiller: prezzo, utili, dividendi e CAPE dal 1871.

Costruire `data/ricerca/mensile_lungo.csv` dal 1927 (S&P giornaliero `sp500`) con le variabili disponibili. Per gli anni in cui una variabile manca, il modello "lungo" usa solo le variabili presenti da quella data.

**Esclusi** (nessuna fonte gratuita affidabile; non cercare oltre): storico delle revisioni degli utili, vendite dei manager, fallimenti settimanali, put/call storico CBOE oltre l'archivio già raccolto.

Ogni nuova serie entra in `semafori.SPEC` con descrizione semplice in italiano e soglie prudenti, nelle famiglie nuove "Salute delle aziende", "Inflazione" e "Liquidità" (più "Mercato interno" se utile). Sono solo monitorate: entrano nell'Indice Armor soltanto con il test automatico già esistente (`armor_index.NEW_IND` + `test_new_indicators`), da estendere a queste serie con la stessa regola.

---

## 4. Obiettivi e misure

- T1: calo ≥10% entro 3, 6 e 12 mesi (minimo dei prezzi giornalieri rispetto al prezzo di partenza).
- T2: calo ≥20% entro 12 mesi (mercato orso).
- T3: direzione a 1, 3, 6 e 12 mesi.
- T4: rendimento sopra o sotto la mediana storica a 6 e 12 mesi.
- T5: recessione USA entro 12 mesi (stadio intermedio).
- Misure:
  - AUC e BSS rispetto alla frequenza di addestramento;
  - diagramma di affidabilità (10 classi);
  - analisi per episodio (§2.8);
  - per la direzione, anche la differenza di rendimento medio tra quintile alto e basso, con t di Newey-West (finestre sovrapposte).

---

## 5. Modelli da provare (dal più semplice)

- M0 riferimenti: frequenza storica, Indice Armor attuale, A1, FHS (`modeleval.py`).
- M1 segnali singoli a soglia fissa e il conteggio dei segnali accesi (0–8). Tabella come in §1, ma con storia lunga.
- M2 logistica L2 per famiglia, che dà un punteggio per famiglia, poi una combinazione con pesi non negativi (stacking walk-forward).
- M3 due stadi:
  - prima la probabilità di recessione entro 12 mesi (probit/logit su curva lunga, spread BAA, sussidi, Sahm, CFNAI, permessi, ritardi sui prestiti). In letteratura questa parte funziona bene: AUC circa 0,85–0,90.
  - poi la probabilità di calo ≥10% e ≥20% data P(recessione), valutazioni, tendenza e paura.
- M4 interazione pre-registrata "caro + deterioramento": valutazioni alte da sole non bastano. Segnale = CAPE nel quintile alto E almeno uno tra utili in calo, spread in allargamento e prezzo sotto la media a 10 mesi.
- M5 analoghi storici (k vicini):
  - prendere i 20–30 mesi passati più simili a oggi (variabili standardizzate solo sul passato, esclusi gli ultimi 12 mesi);
  - mostrare cosa è successo dopo: % di rialzi a 6 e 12 mesi, mediana, 10° e 90° percentile, % di cali ≥10%;
  - validare come gli altri. È la forma più chiara per dare una "tendenza" precisa al posto di "±X%".
- M6 gradient boosting monotono (solo se batte M2/M3 in tutti i sottoperiodi).
- Taratura: Platt in walk-forward annidato; isotonica solo con almeno 30 eventi nel periodo di taratura.
- Media dei modelli che passano le regole (pesi uguali), da preferire al singolo migliore.

Codice: nuovo modulo `src/armor/ricerca.py`, comando `python -m armor ricerca` in `jobs.py`. Scrive `data/ricerca/risultati.json`, `registro_prove.csv`, `episodi.json` e `analoghi_oggi.json`. Nuovo workflow `.github/workflows/ricerca.yml`, manuale e mensile, timeout 60 minuti, stesso schema di `valida.yml`, salvataggio con `bash scripts/salva.sh "Ricerca modello" data`.

---

## 6. Regole di adozione (decise prima di vedere i risultati)

- Modalità ombra (`shadow.py`, `data/journal_shadow.csv`): entra un modello che su 1960–2018 o 2000–2018 ha BSS > 0 e AUC ≥ riferimento + 0,02 in almeno 2 di 3 sottoperiodi, senza peggioramenti oltre 0,02.
- Numeri principali dell'app: solo dopo il test unico sull'hold-out 2019–2026, con BSS > 0 e AUC ≥ Indice Armor allo stesso orizzonte. Comunicarlo all'utente con i numeri prima e dopo.
- Indice Armor: nuove serie solo tramite `test_new_indicators` (AUC +0,01 in almeno 2 eventi su 3, nessuno sotto −0,01).
- Direzione: si mostra una tendenza su/giù solo se un modello ha BSS > 0,01 fuori campione e sull'hold-out. Altrimenti resta la presentazione onesta (frequenza storica + analoghi + rischio di cali).

---

## 7. Cosa mostrare nell'app (Fase C)

- Oggi, riquadro "Rischio ciclico 6–12 mesi":
  - elenco dei segnali classici accesi o spenti (utili, credito, ritardi sui prestiti, sussidi, curva, tendenza, valutazioni, inflazione, liquidità, leva), ciascuno con le frequenze storiche "acceso/spento" (calo ≥10% in 6 mesi; S&P a 12 mesi);
  - il livello del modello (basso, medio o alto rispetto alla storia; in % solo se tarato e adottato).
- Oggi, riquadro "Mesi del passato più simili a oggi": "Nei 25 mesi più simili, dopo 12 mesi l'S&P era salito in X casi su 25 (mediana +Y%), con un calo ≥10% lungo la strada in Z casi". Elenco dei mesi, cliccabile.
- Semafori: nuove famiglie con testi semplici. Mappa termica: righe delle nuove famiglie (`mappa.build_mappa` extras, con `ni=1` finché non sono nell'Indice).
- Fiducia: sezione "Ricerca modello" con:
  - tabella dei risultati per obiettivo e orizzonte;
  - numero di prove fatte;
  - analisi per episodio;
  - cosa è stato adottato e perché, o perché no.
- Contrasto alto: mai testo viola o scuro su fondo nero; testo `var(--tx)`. Pagine pesanti caricate a richiesta (`lazy_pages`, `site/series/*.json`). Bump della cache in `web/sw.js`.

---

## 8. Fasi e consegne

1. Patch 21 — dati:
   - `sources.py` (nuovi codici FRED/Yahoo, ECB CISS, FINRA, Shiller esteso);
   - `fondamentali.py` (derivate + tabella `LAG` dei ritardi);
   - raccolta giornaliera di `rev_breadth`/`fwd_growth` nel ciclo giornaliero (timeout 90 s);
   - voci in `semafori.SPEC` (solo monitorate);
   - `ricerca.py` + comando + `ricerca.yml` (anche in forma iniziale);
   - test in `tests/test_armor.py` per derivate, ritardi e parsing (con dati finti, nessuna rete);
   - aggiornare `CONTINUA_DA_QUI.md`.

   All'utente: push, poi lanciare "Aggiornamento giornaliero Armor" (scarica tutto lo storico delle serie nuove), poi [PowerShell] `cd D:\Armor; git pull --no-rebase`.
2. Fase B — ricerca nel cloud (nessuna patch finché non ci sono risultati):
   - comprimere e caricare `data/series` (`scripts/copia_cloud.py serie`);
   - eseguire `ricerca.py` su 1960–2018 e 2000–2018;
   - registrare tutto;
   - iterare sulle leve di §1;
   - scrivere i risultati in `CONTINUA_DA_QUI.md`.

   Se i dati scaricati mancano o sono vuoti, chiedere all'utente le righe `[dati]` del log Actions.
3. Patch 22 — integrazione:
   - modelli promossi in ombra;
   - riquadri in Oggi, sezione in Fiducia, semafori e mappa;
   - screenshot a 430px;
   - workflow "Ricerca modello" da lanciare.
4. Patch 23 — hold-out:
   - test unico 2019–2026;
   - decisione di adozione secondo §6;
   - messaggio all'utente con numeri chiari: abilità prima e dopo, per orizzonte, e cosa resta imprevedibile.

---

## 9. Promemoria per l'agente

- Non promettere precisione che i dati non danno. Dai numeri verificati, in parole semplici: "su 100 confronti il modello indica come più rischioso il mese giusto 72 volte; 50 = caso".
- Mai "±X%" da solo: sempre la fascia tarata, la frequenza storica di rialzo, gli analoghi e il rischio di cali.
- Se una fonte non risponde da Actions, l'app deve funzionare comunque (ultimo dato noto, `salute.py` segnala il ritardo).
- Ogni nuova variabile ha una frase in italiano semplice che spiega cosa misura e perché conta.
