# Istruzioni per Claude Cowork — Prossimo ciclo di sviluppo Armor

Claude: lavora direttamente sul repository Armor allegato. Prima di modificare codice, leggi integralmente `AUDIT_ARMOR_ENDOGENO_2026-11-24.md`, `CONTINUA_DA_QUI.md` e i protocolli di ricerca esistenti. Non rimuovere né riscrivere risultati negativi già registrati.

## Obiettivo

Migliorare il rilevamento anticipato delle vulnerabilità endogene che possono evolvere in stress finanziario e drawdown importanti su S&P 500 e VWCE. Il sistema deve distinguere:

1. vulnerabilità strutturale che si accumula lentamente;
2. stress finanziario effettivamente in aumento;
3. conferma interna del mercato;
4. stabilizzazione/accumulazione dopo il ribasso.

Non promettere la previsione certa del giorno del crollo. Non modificare gli score in produzione finché un nuovo modello non supera il protocollo OOS.

## Vincoli inderogabili

- Non usare dati futuri, revisioni macro non disponibili allora, membership corrente degli indici applicata al passato, né feature derivate da valori successivi.
- Ogni serie macro deve avere una `available_at`/publication lag documentata. Per FRED riveduti, dichiarare esplicitamente che il dato non è vintage point-in-time.
- Ogni etichetta deve definire indice, valuta, soglia, orizzonte, metodo del drawdown, finestra iniziale e trattamento dei dati incompleti.
- Non contare le osservazioni mensili sovrapposte come crisi indipendenti. Raggruppare gli episodi e riportare il numero di episodi effettivi.
- Non promuovere un modello per AUC soltanto. Brier Skill, calibrazione, PR-AUC, falsi allarmi e lead-time sono obbligatori.
- Nessun indicatore nuovo deve influenzare Titan, Super Armor o Indice crollo senza protocollo pre-registrato, test OOS e approvazione esplicita.

## Fase 1 — Convalida dati BIS DSR

1. Esegui un aggiornamento completo in un branch di sviluppo e verifica la risposta live dell'API BIS.
2. Controlla che siano salvate le serie `bis_dsr_us_private`, `bis_dsr_us_households`, `bis_dsr_us_corporate`, `bis_dsr_xm_private`, `bis_dsr_jp_private`, `bis_dsr_gb_private`, `bis_dsr_ca_private` quando disponibili.
3. Verifica che i dati siano trimestrali, che le date siano fine trimestre e che i valori corrispondano ai CSV/portale BIS per un campione casuale.
4. Registra l'ultima osservazione, data di rilascio e ritardo applicato. BIS aggiorna il DSR trimestralmente: non trattare la data di fine trimestre come data di conoscenza pubblica.
5. Se l'API v1 smette di funzionare, migra al BIS SDMX API v2 seguendo la documentazione ufficiale. Non fare fallback silenzioso a dati incompleti.
6. Mantieni il DSR in peso zero finché non c'è una prova storica e forward sufficiente.

## Fase 2 — Ricostruzione point-in-time e data-quality

1. Genera un inventario macchina-lettura di ogni serie: fonte, frequenza, data iniziale/finale, date mancanti, revisionabilità, lag, copertura, duplicati, unità e trasformazioni.
2. Separa `observation_date` da `available_date`. Per dati trimestrali/mensili, usa il calendario di pubblicazione quando disponibile; in mancanza usa un lag prudenziale e dichiaralo.
3. Elimina dalle prove primarie tutte le breadth `d_*` costruite da componenti correnti. Lasciale solo in un test di sensibilità marcato `SURVIVORSHIP_BIASED`.
4. Per il VWCE, costruisci proxy separate e documentate per USA, Europa, Giappone, emergenti e cambio EUR/USD. Mostra come cambia il risultato usando VWCE reale dal 2019, VT/EURUSD e proxy regionali.
5. Aggiungi controlli automatici che falliscono se una feature supera la data di disponibilità o se un target non è maturato prima del training cut-off.

## Fase 3 — Etichette di evento

Costruisci due insiemi distinti:

A. `market_drawdowns`: drawdown futuri quantitativi (es. -8/-10/-15/-20% a 1/3/6/12 mesi), indipendenti dalla causa.

B. `endogenous_crisis_events`: catalogo eventi con data d'inizio, picco, minimo, recupero, asset/area, meccanismo dominante, meccanismi secondari, severità e classificazione `endogenous`, `exogenous`, `mixed`, `uncertain`.

La classificazione causale deve essere documentata con fonti pubbliche e stabilita prima di valutare i segnali. Non includere o escludere gli eventi per far apparire migliore il modello. Fare analisi di sensibilità con e senza eventi misti/esogeni.

Studia anche la durata: un bear market lungo non coincide con il solo drawdown massimo. Definisci separatamente durata picco-recupero, drawdown persistente e recovery-time.

## Fase 4 — Nuova architettura di segnali (shadow mode)

Costruisci quattro sottosistemi autonomi, senza mediare tutto in un unico numero:

1. `VULNERABILITY`: DSR relativo alla propria storia, credit-to-GDP gap, leva, valutazioni, concentrazione, copertura interessi, scadenze debito, capex/free cash flow, fragilità finanziaria di intermediari.
2. `FINANCIAL_STRESS`: spread HY/IG, deterioramento NFCI/ANFCI/STLFSI/CISS, standard bancari, funding stress, repo/mercato monetario, VIX term structure e MOVE.
3. `INTERNAL_MARKET_CONFIRMATION`: RSP/SPY, small caps/SPY, banche/SPY, settori ciclici/difensivi, nuovi minimi, breadth point-in-time, dispersione e correlazioni.
4. `ACCUMULATION_READINESS`: prezzo già corretto, stress che smette di peggiorare, normalizzazione del credito/volatilità, breadth che recupera. Deve essere distinto dal rischio di ulteriore ribasso.

Ogni fattore deve esporre valore, percentile storico, variazione, persistenza, copertura e timestamp di disponibilità. Se un dato è assente, non imputarlo come “normale”: segnare `missing` e ridurre la confidenza.

## Fase 5 — Prova modelli

Confronta almeno:

- frequenza di base storica;
- Logistic Regression L1/L2 con regolarizzazione forte;
- HistGradientBoosting/Gradient Boosting con profondità contenuta;
- Random Forest/Extra Trees con vincoli di profondità e foglia;
- discrete-time hazard o survival model per il tempo all'evento;
- HMM/Markov switching come classificatore di regime, senza confonderlo con la probabilità di crisi;
- ensemble calibrato soltanto se supera singole componenti fuori campione.

XGBoost/LightGBM/CatBoost sono facoltativi: introdurli solo dopo test di runtime e dipendenze nelle GitHub Actions. Evitare una ricerca enorme di iperparametri. Se vengono provate molte varianti, stimare la distribuzione del massimo risultato ottenibile per caso.

Valutazione obbligatoria:

- walk-forward temporale;
- embargo specifico dell'orizzonte;
- blocchi temporali OOS non sovrapposti;
- almeno un test finale congelato;
- Brier Score e Brier Skill rispetto a baseline;
- calibration curve/reliability diagram;
- ROC-AUC e PR-AUC (con prevalenza di base mostrata);
- precision, recall e tasso di eventi nel top 5/10/20%;
- falsi allarmi per anno, quota di giorni/mesi in allarme, lead-time medio;
- recall per episodio di crisi, non solo per riga;
- intervalli d'incertezza con block bootstrap per preservare autocorrelazione;
- stabilità per regime e sottoperiodo.

Usa le regole del report audit come baseline: non indebolire i criteri già esistenti. Un modello che ha AUC maggiore ma Brier Skill negativo non è un miglioramento operativo.

## Fase 6 — Test della strategia di versamenti extra

Solo dopo avere un modello probabilistico convalidato, testare la politica di versamenti extra. Non vendere e non ridurre il PAC di base. Confrontare:

- PAC standard sempre investito;
- PAC + riserva cash investita a date fisse;
- PAC + extra su drawdown a soglie fisse (-5/-10/-15/-20%);
- PAC + extra da `ACCUMULATION_READINESS`;
- PAC + regola guidata da probabilità di drawdown/rischio.

Includere commissioni, spread, fiscalità italiana, rendimento netto della liquidità, FX, dividendi e date di esecuzione realistiche. Usare stesso capitale complessivo e stessi flussi esterni. Misurare CAGR/XIRR, max drawdown, tempo sotto acqua, rischio di esaurimento della riserva e rendimento per euro investito. Evitare qualsiasi confronto che dia più capitale a una strategia.

## Fase 7 — UI e produzione

- Mostrare separatamente vulnerabilità, stress, conferma e accumulazione.
- Mostrare i contributori principali, non solo lo score.
- Visualizzare qualità/aggiornamento dei dati e missingness.
- Ogni previsione deve salvare timestamp, versione, probabilità, target, orizzonte e versione del modello in un registro immutabile.
- Etichette chiare: `DESCRITTIVO`, `SPERIMENTALE`, `VALIDATO`, `NON VALIDATO`.
- Iniziare in `shadow mode` per almeno 6-12 mesi e non cambiare le soglie durante il test.

## Deliverable richiesti

1. Audit dati e gap di copertura.
2. Catalogo eventi con fonti e classificazione causale.
3. Nuovi moduli e test unitari.
4. Backtest OOS con report completo, incluso ogni risultato negativo.
5. Analisi dei falsi positivi e dei casi mancati.
6. Piano di rollout shadow/produzione.
7. Diff chiaro di tutti i file modificati.

Non considerare il compito completato con una nuova formula di score o un grafico più bello. Il compito è completato solo se i nuovi dati si aggiornano, i test sono riproducibili e le previsioni migliorano davvero rispetto alle baseline su episodi non usati nella progettazione.
