# ARMOR — Audit tecnico e piano di miglioramento per il rischio endogeno

**Data:** 24 novembre 2026  
**Ambito:** codice ZIP consegnato, report tecnico Armor aggiornato al 24/11/2026, archivio locale `data/series`.  
**Obiettivo:** riconoscere l'accumulo di vulnerabilità e lo stress interno del sistema finanziario che possono precedere drawdown importanti su S&P 500 e VWCE, mantenendo il PAC come benchmark.

## 1. Verdetto dell'audit

Armor è già un'applicazione quantitativa ampia: circa 40.000 righe Python, oltre 150 moduli, aggiornamenti schedulati, archivio storico, previsioni, indici di rischio e prove walk-forward. Il problema non è principalmente la scarsità di indicatori. È la scarsità di episodi indipendenti e la difficoltà di trasformare segnali di fragilità in probabilità di crisi ben calibrate e stabili fuori campione.

La conclusione del report esistente resta valida: gli indici descrivono lo stress corrente meglio di quanto anticipino il momento dei crolli; le strategie di market timing e i versamenti extra attivati dai segnali già testati non hanno battuto il PAC semplice dopo costi e tasse. La nuova ricerca non deve cancellare questo risultato.

**Decisione implementativa:** nessun nuovo modello entra negli indici in produzione e nessun peso di Titan/Super Armor/Indice crollo viene modificato. È stato aggiunto un canale sperimentale per il Debt Service Ratio BIS e un laboratorio ripetibile. Entrambi restano separati dal sistema operativo fino a una prova indipendente convincente.

## 2. Cosa ho verificato nel progetto

- Struttura `src/armor` e moduli già presenti: `model.py`, `model_mv.py`, `modello_sistemico.py`, `crisi_lente.py`, `concentrazione.py`, `territori.py`, `indice_crollo.py`, `fhs.py`, `titan.py`, `super_armor.py`, `features.py`, `sources.py`, `store.py` e altri.
- Archivio di circa 1.844 CSV in `data/series`.
- Serie lunghe disponibili: S&P 500 dal 1927; VIX/SKEW dal 1990; NFCI e sue componenti dagli anni Settanta; richieste iniziali di sussidi dagli anni Sessanta; CISS europeo dal 1980; spread di credito e serie cross-asset con coperture differenti.
- Dati di breadth `d_*` costruiti su componenti correnti: non sono adatti come prova storica primaria perché la composizione corrente applicata al passato introduce survivorship bias.
- Numerose serie dell'archivio recente non entrano ancora nei modelli in produzione: l'archivio è più ricco dei segnali effettivamente usati.
- Le serie macro FRED sono storiche riviste, non vere vintage point-in-time. Applicare un ritardo di pubblicazione riduce il rischio di look-ahead ma non ricrea ciò che il mercato conosceva in ogni data storica.

Il report consegnato segnala inoltre che i test precedenti non hanno dimostrato i sette territori endogeni e che il modello dei ribassi lenti, pur avendo una AUC storica promettente, ha mancato la soglia d'allarme prima dei tre episodi esaminati. Questi fallimenti sono evidenza da preservare, non da nascondere.

## 3. Nuovo esperimento riproducibile

È stato aggiunto `scratch/armor_endogenous_lab.py`. Il laboratorio non modifica gli indici di produzione. Campiona le ultime sedute di ogni mese quando il mercato è entro il 5% dal massimo degli ultimi 252 giorni e testa tre obiettivi:

| Etichetta | Orizzonte | Evento cercato |
|---|---:|---:|
| `dd63_8` | 63 sedute | drawdown futuro massimo almeno -8% |
| `dd126_10` | 126 sedute | drawdown futuro massimo almeno -10% |
| `dd252_15` | 252 sedute | drawdown futuro massimo almeno -15% |

I modelli confrontati sono Logistic Regression L2 e HistGradientBoosting, in gruppi distinti: sole variabili prezzo; credito/finanziamento; relazioni cross-asset e interni di mercato; combinazione dei gruppi; sensibilità alle serie breadth. Il laboratorio usa walk-forward mensile, refit periodico, probabilità base calcolata solo sul training e embargo specifico per l'orizzonte (100/200/380 giorni). Le finestre future incomplete sono escluse, non etichettate come non-eventi.

**Nota essenziale:** queste etichette sono proxy di drawdown, non classificazioni certificate di crisi endogene. Un calo di prezzo non rivela da solo se la causa sia interna, esterna o mista. La proxy VWCE usa VT convertito in euro prima della storia effettiva di VWCE e ha un campione valutabile molto più corto.

## 4. Risultati del test locale

### S&P 500

- Per `dd63_8`, il miglior risultato osservato è `cross_asset_internal` + HistGradientBoosting: AUC 0,647, ma Brier Skill rispetto alla frequenza di base solo +0,0073, su 96 previsioni, 18 mesi positivi e circa 6 cluster di eventi. È un miglioramento minuscolo, non sufficiente per un allarme.
- Per `dd126_10`, il miglior risultato è il modello prezzo + HistGradientBoosting: AUC 0,534 e Brier Skill +0,0049 su 141 previsioni e 31 positivi. È sostanzialmente vicino alla baseline.
- Per `dd252_15`, il modello credito/finanziamento + Logistic Regression arriva ad AUC 0,616, ma Brier Skill -0,0555: ordina parzialmente i casi, però produce probabilità peggiori della baseline. Il campione di test ha 136 previsioni, 28 positivi e circa 4 cluster approssimati.

### Proxy VWCE in euro

- Per `dd63_8`, il modello prezzo + HistGradientBoosting mostra AUC 0,840 e Brier Skill +0,0789, ma su sole 47 previsioni, 4 mesi positivi e circa 2 cluster. Non è evidenza sufficiente: pochi eventi rendono il risultato altamente instabile.
- Per `dd126_10` e `dd252_15`, le famiglie di modelli testate non mostrano un vantaggio stabile; il Brier Skill è generalmente negativo.

### Lettura corretta

Non emerge un modello da promuovere. I singoli picchi di AUC non bastano: per un sistema di allerta contano calibrazione, Brier Skill, precision-recall, tasso di eventi nelle fasce alte, recall degli episodi, falsi allarmi per anno e anticipo medio. Le stime di cluster sono approssimative e non sostituiscono un catalogo di episodi indipendenti.

Il gruppo `breadth_sensitivity_only` su S&P 500 replica i risultati di `all_core`: le serie breadth non superano il filtro di disponibilità del 60% nel campione di training. Non si deve quindi attribuire a questi test un miglioramento da breadth.

Il file `scratch/armor_endogenous_lab_result.json` conserva l'output analitico prodotto il 24/11/2026. Per ripetere l'esperimento:

```bash
PYTHONPATH=src python scratch/armor_endogenous_lab.py
```

## 5. Nuova sorgente: BIS Debt Service Ratio

È stato aggiunto `src/armor/bis_dsr.py` e collegato all'aggiornamento ordinario in `src/armor/sources.py`.

Le serie previste sono:

- Stati Uniti: totale settore privato non finanziario, famiglie, società non finanziarie;
- Area euro, Giappone, Regno Unito e Canada: totale settore privato non finanziario.

Il DSR misura i costi di servizio del debito in rapporto al reddito. La BIS pubblica le osservazioni trimestralmente e raccomanda di confrontare il DSR di ciascun paese soprattutto con la propria storia, non di confrontare meccanicamente i livelli tra paesi, perché la metodologia incorpora ipotesi semplificatrici sulle scadenze medie. La letteratura BIS trova che DSR e credit-to-GDP gap possono essere utili come early-warning indicator, con orizzonti e vantaggi differenti.

**Stato:** parser e fallback sono coperti da test sintetici; la chiamata live alla BIS non è stata eseguita in questo ambiente. Il primo aggiornamento da GitHub Actions deve confermare che le serie vengano effettivamente restituite e salvate. Finché non c'è un archivio sufficiente e un test point-in-time, il DSR è sperimentale e ha peso zero.

La trasformazione sperimentale in laboratorio usa livello, variazione annuale e z-score mobile a 20 trimestri, con ritardo conservativo di 120 giorni. Non utilizzare i livelli assoluti come confronto diretto tra paesi.

## 6. Architettura che raccomando per la prossima versione

Non comprimere tutto in un unico punteggio lineare. Separare almeno quattro livelli:

1. **Vulnerabilità strutturale (lenta):** eccesso di credito, DSR, valutazioni, leva, concentrazione, dipendenza dal finanziamento a breve, fragilità dei bilanci.
2. **Stress finanziario (medio/veloce):** spread, condizioni bancarie, volatilità implicita e sua curva, funding stress, liquidità, correlazioni e flight-to-quality.
3. **Conferma di mercato (prezzo):** breadth senza survivorship bias, nuovi minimi, dispersione, correlazioni, trend e drawdown. Il prezzo deve confermare, non essere l'unica causa dell'allarme.
4. **Fase di accumulazione (separata):** panico già avvenuto, stress che smette di peggiorare e segnali di stabilizzazione. Non confondere il rischio di un ulteriore ribasso con la convenienza di un acquisto extra.

Proporre un allarme solo se si verifica una combinazione predefinita e persistente di vulnerabilità + stress + conferma, ma i pesi e le soglie vanno appresi e congelati nel training e convalidati fuori campione. Non imporre a priori che la convergenza di più segnali sia predittiva: il report precedente mostra che una regola semplice di convergenza non ha funzionato.

### Modelli da valutare nel ciclo successivo

- Logistic Regression regolarizzata come baseline interpretabile.
- HistGradientBoosting / Gradient Boosting con profondità contenuta.
- Random Forest / Extra Trees con vincoli severi, solo come sfidanti.
- Modello di regime HMM o Markov-switching: regime latente distinto dal rischio di evento; da introdurre solo con dipendenza disponibile e test riproducibili.
- Discrete-time hazard / survival model per il tempo all'evento, preferibile a classificare ogni giorno come osservazione indipendente.
- Ensemble soltanto se migliora la calibrazione fuori campione rispetto alle singole componenti.

Non aggiungere XGBoost/LightGBM/CatBoost a GitHub Actions solo perché disponibili localmente: prima valutare dipendenze, tempo di esecuzione, riproducibilità e vantaggio su holdout.

## 7. Protocollo minimo per promuovere un modello

1. Definire etichette evento e orizzonte prima del test; distinguere crisi endogene, esogene e miste tramite una tassonomia documentata, non classificandole dopo aver visto il segnale.
2. Campionare al massimo una data per mese per la ricerca early-warning e misurare anche gli episodi di crisi, non solo le righe giornaliere sovrapposte.
3. Usare walk-forward con embargo almeno pari al periodo in cui il target futuro resta non osservabile; per orizzonti lunghi usare embargo specifico e test temporali non sovrapposti.
4. Confrontare sempre con baseline a prevalenza storica, modelli attuali Armor, buy-and-hold/PAC e un placebo che preservi il clustering temporale.
5. Riportare Brier Skill, calibration curve, PR-AUC contro prevalenza, AUC, precision/recall, falsi allarmi annui, quota di tempo in allarme, lead-time e intervalli d'incertezza con block bootstrap.
6. Separare training, selezione e test finale; nessuna selezione di feature o soglia sul test finale. Correggere il multiple testing: se si provano decine di segnali, confrontare il vincitore con la distribuzione del migliore ottenuto per caso.
7. Ripetere per regimi e sotto-periodi, incluse fasi inflazionistiche, bassa inflazione, crisi di credito e shock esterni. Se il vantaggio dipende da un singolo episodio, non promuovere.
8. Testare dati point-in-time: revisioni macro, data di pubblicazione, ritardi ETF e disponibilità effettiva dei componenti storici.

Soglia di accettazione proposta: Brier Skill positivo rispetto alla baseline in entrambi i blocchi temporali, intervallo d'incertezza non compatibile con un deterioramento sostanziale, PR-AUC superiore alla prevalenza, numero di eventi indipendenti sufficiente e un vantaggio operativo netto in un backtest separato. I criteri attuali del progetto (miglioramento minimo sul Brier e non peggioramento AUC) possono essere mantenuti e resi più stringenti, non indeboliti.

## 8. Dati prioritari da aggiungere o verificare

- BIS DSR (nuovo collector sperimentale) e aggiornamento/qualità del credit-to-GDP gap già presente.
- Dati di composizione storica degli indici e breadth point-in-time. Fino ad allora usare proxy robuste come RSP/SPY, small caps/SPY, banche/SPY, settori ciclici/difensivi, non le componenti attuali applicate retroattivamente.
- Flussi e posizionamento con data di pubblicazione effettiva; i 13F sono ritardati e non sono un sensore tempestivo di uscita.
- Funding e credito: NFCI/ANFCI, STLFSI, spread HY/IG, survey bancarie, CISS, misure di mercato monetario. Distinguere costo del credito da disponibilità di credito.
- Bilanci e flussi di cassa: leva netta, copertura interessi, scadenze del debito, liquidità e capex rispetto al cash flow; trattare le aziende AI come un sottoinsieme e non come l'intero mercato.
- VWCE: modellare separatamente USA, Europa, Giappone, emergenti e cambio EUR/USD; un proxy statunitense non è un sostituto perfetto dell'ETF globale in euro.

## 9. Modifiche incluse nello ZIP

- `src/armor/bis_dsr.py`: collector BIS DSR, parser SDMX, fallback per singole aree e settori.
- `src/armor/sources.py`: aggiornamento DSR durante il flusso completo e aggiornamento mirato.
- `tests/test_bis_dsr.py`: test parser, date trimestrali, risposta incompleta e fallback serie mancanti.
- `pytest.ini`: abilita il layout `src/` con il comando standard pytest.
- `scratch/armor_endogenous_lab.py`: laboratorio walk-forward sperimentale.
- `scratch/armor_endogenous_lab_result.json`: risultato del laboratorio del 24/11/2026.
- `AUDIT_ARMOR_ENDOGENO_2026-11-24.md` e `PROMPT_CLAUDE_COWORK_ARMOR.md`.

## 10. Test eseguiti e limiti

Comando eseguito:

```bash
pytest -q tests/test_bis_dsr.py tests/test_modello_sistemico.py tests/test_territori.py tests/test_concentrazione.py tests/test_indice_crollo.py tests/test_titan.py
```

Esito: **33 passed**. La suite completa non è stata completata entro il limite di esecuzione di questa sessione; non affermo quindi che l'intero repository sia testato end-to-end. Il collector BIS è stato testato con payload SDMX sintetici, non con una chiamata live. Dopo il primo run di GitHub Actions va controllato `data/status.json` e verificato che `bis_dsr_*` abbia date trimestrali aggiornate.

**Conclusione:** questa consegna migliora la raccolta di un fattore di credito rilevante e rende ripetibile una nuova batteria di test; non ha ancora dimostrato un modello capace di anticipare i crolli endogeni. È deliberato: è meglio mostrare “non abbiamo un vantaggio misurabile” che produrre un allarme rassicurante ma non affidabile.
