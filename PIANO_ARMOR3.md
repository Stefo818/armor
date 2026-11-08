# PIANO ARMOR 3 — rischio coerente, onesto e utile per il PAC

Documento di lavoro per l'agente che sviluppa Armor (Sonnet). Va letto per intero, insieme alle ultime 3 sezioni di `CONTINUA_DA_QUI.md`
e alla sezione 0 di `PIANO_MODELLO.md` (regole del progetto: copia di lavoro, test, zip, consegna, istruzioni all'utente).
Nasce dal confronto tra quattro revisioni del report tecnico (Claude, GPT, Gemini, DeepSeek) e da due misure fatte sul codice reale (§2).

**Obiettivo.** Non prevedere la direzione (nessuno dei modelli provati ci riesce, §1). L'obiettivo è dare:
- probabilità di perdita, drawdown e rendimento coerenti tra orizzonti e soglie;
- probabilità verificate con statistiche oneste, che tengano conto delle finestre sovrapposte e del numero di prove fatte;
- il rischio di VWCE in euro, cioè dell'investimento reale;
- la dichiarazione esplicita di quando la stima è poco affidabile;
- la traduzione in scenari per chi accumula con un PAC.

---

## 0. Regole che valgono per tutto il piano

1. **Il modello principale non si cambia senza una verifica documentata.** Ruoli:
   - **Riferimento ufficiale**: quello che l'app mostra come numero principale.
   - **Sfidante**: mostrato accanto, etichettato «sperimentale».
   - **Ombra**: calcolato e registrato, non mostrato come previsione.
2. **Il 2019-2026 non è più un campione pulito**: è già stato visto. Per le adozioni future conta il diario dal vivo, giudicato con un protocollo scritto prima di guardare i risultati (§3, Fase 1).
3. **Pre-registrazione.** Regole, soglie, varianti da confrontare e metriche si scrivono nel codice e in `CONTINUA_DA_QUI.md` prima di lanciare un test. Ogni prova va nel registro (`data/ricerca/registro_prove.csv`), anche quelle fallite.
4. **Mai promettere miglioramenti prima del test.** Per ogni intervento il piano dice se è:
   - **[solido]**: motivazione teorica o difetto misurato;
   - **[ipotesi]**: da verificare;
   - **[sperimentale]**.
5. **Niente medie arbitrarie tra modelli** e niente pesi inventati: quando due modelli divergono, la divergenza si mostra.
6. **Non riscrivere l'app.** Moduli nuovi accanto a quelli esistenti; i vecchi restano in ombra finché il nuovo non è adottato.
7. **Consegna**: una patch per fase (patch 26, 27, …).
   - Test verdi (`python3.11 -m compileall -q src tests` e `python3 -m pytest -q tests`); `ruff check src` se disponibile, senza bloccare.
   - Screenshot a 430px per le parti visibili, contrasto alto.
   - `CONTINUA_DA_QUI.md` aggiornato con tutti i numeri, anche negativi.
   - Istruzioni all'utente a blocchi [PowerShell]/[Chrome]/[Telefono], con i comandi per intero.

---

## 1. Da dove si parte (patch 25, novembre 2026)

| Orizzonte (sedute) | Riferimento | Abilità misurata |
|---|---|---|
| 10 giorni (7) | A1 | AUC 0,72 |
| 1 mese (21) | A1 / FHS+VIX | AUC 0,76 / 0,79 |
| 3 mesi (63) | A1 / FHS+VIX | AUC 0,67 / 0,70 |
| 6 mesi (126) | A1 | AUC 0,63 |

- A1 è una regressione logistica su 8 variabili di prezzo dell'S&P 500, con storia dal 1928.
- FHS è un GJR-GARCH-t con residui ricampionati; FHS+VIX sposta la varianza iniziale verso il VIX (peso 0,5, premio di volatilità 0,8).
- Gli AUC vengono dalla verifica walk-forward 1994-2026, con una previsione ogni 5 sedute.

Altri punti fermi:
- Direzione su/giù: nessun modello batte la frequenza storica.
- 6-12 mesi: nessun modello ha superato la prova finale 2019-2026. In quel periodo Indice Armor e A1 hanno AUC sotto 0,5 su campioni mensili con 13-34 eventi.
- Patch 24: FHS+VIX usato a 1 e 3 mesi come numero principale. La regola che l'ha scelto era stata fissata guardando la stessa tabella: va corretto (Fase 0).
- Probabilità oggi (8/11/2026, VIX 25,6), calo ≥10%:
  - entro 1 mese: A1 3%, FHS+VIX 11%;
  - entro 3 mesi: A1 8%, FHS+VIX 24%.

---

## 2. Correzioni ai pareri delle quattro revisioni (misure fatte sul codice reale)

Due misure fatte l'8/11/2026 con `fhs.fit` (S&P 500 dal 1950) e `fhs.simulate` (20.000 percorsi a 252 sedute):

| Grandezza | Valore misurato |
|---|---|
| Parametri | alpha 0,025, gamma 0,121, beta 0,904, nu 6,9 |
| Persistenza alpha + gamma/2 + beta | 0,989 → emivita di uno shock circa **63 sedute** |
| Volatilità di lungo periodo / di oggi | 16,0% / 29,1% annua |
| Percorsi partiti dalla varianza media: quantili 10/50/90 a 252 sedute | -10% / +11% / +29% (storia 1950-2026: -12% / +11% / +29%) |
| Stessi percorsi: calo ≥10% / ≥20% entro 252 sedute | 30% / 12% (storia 31% / 12%) |
| **Code dei percorsi** | eccesso di curtosi dei rendimenti logaritmici 50-75 a 126-252 sedute (storia, finestre non sovrapposte: 1-3). Percorsi estremi da -98% a +900% |
| Partenza dalla varianza di oggi: calo ≥10% entro 63 sedute | 28,5% (frequenza storica 11%) |

| Tema | Pareri | Decisione |
|---|---|---|
| Emivita del GARCH | Gemini: 15-40 sedute; DeepSeek: 22 | Misurata: circa 63 sedute. Va calcolata e registrata a ogni stima, non assunta (GPT ha ragione). |
| FHS esteso a 252 sedute | DeepSeek: le code esplodono, serve un FHS di lungo periodo | **Confermato dalla misura.** Il centro della distribuzione e le probabilità di calo tornano con la storia; le code no. Va corretto prima di usarlo per 252 sedute e soprattutto per il PAC, dove i percorsi a +900% gonfiano le medie. |
| VIX e VIX3M | Gemini: VIX per i giorni 0-21, VIX3M per 22-63 | Sbagliato: VIX3M è la volatilità media a 3 mesi, non quella tra il secondo e il terzo mese. Si usa la varianza forward: σ²(30→90) = (T90·σ90² − T30·σ30²)/(T90 − T30), poi corretta per il premio di volatilità stimato sui dati (GPT ha ragione). |
| Conversione in euro | Gemini: livello × F(t−1)/F(t) | Sbagliato. Corretto: livello in euro = livello in dollari / F(t), oppure rendimento 1 + r€ = (1 + r$)·F(t−1)/F(t), con F = dollari per euro. Verificare che `features.vwce_series()` faccia la divisione sul livello. |
| PBO (Probability of Backtest Overfitting) | GPT/DeepSeek: usarlo; Claude: solo per strategie | Correzione di Claude: con il metodo CSCV si applica a qualsiasi metrica, anche al punteggio di Brier, su più configurazioni e blocchi di tempo. Si usa. Il Deflated Sharpe invece non si applica (Armor non produce rendimenti di strategia). |
| Variance risk premium (VRP) | Tutti: testarlo; DeepSeek: separare notte e giorno | VRP = varianza implicita (VIX²) − varianza fisica attesa sullo stesso orizzonte, prevista ex ante, non quella passata. Senza dati intraday gratuiti si usa lo stimatore Yang-Zhang da apertura/massimo/minimo/chiusura: separa la parte notturna da quella di seduta. |
| VWCE in euro, effetto dollaro | Tutti d'accordo | Le cifre del 2022 citate non sono state verificate: non vanno inserite nel codice. Il motore su dati in euro cattura l'effetto da solo. |
| «Sacche di prevedibilità» per regime | DeepSeek | **[ipotesi]**: solo come test di interazione pre-registrato con i regimi esistenti (calma/tensione/crisi), in fondo alla lista. |
| Hazard model, teoria dei valori estremi, PCA/fattori latenti, reti neurali, HMM | Tutti, alla fine | Rinviati: pochi eventi (6-20 grandi cali) e tentativi simili già falliti. |

---

## 3. Fasi

### Fase 0 — Rimettere in ordine la patch 24 (patch 26, piccola) [solido]

- **A1 torna riferimento ufficiale a tutti gli orizzonti.**
  - In `jobs.forecast()`, `campioni.applica()` non deve più sostituire le probabilità.
  - Calcolare FHS+VIX a parte e salvarlo in `pred[hz]["sfidante"] = {"motore": "FHS+VIX", "p": {...}}`.
- **Schede delle previsioni** (`chiaro.horizon_simple`):
  - numero principale = A1;
  - riga «Modello sperimentale in prova (FHS+VIX): X%»;
  - badge «Divergenza» quando |FHS+VIX − A1| ≥ 5 punti e il rapporto è ≥ 2, con la spiegazione: «la simulazione guidata dalla volatilità di oggi vede più stress del modello sulla tendenza dei prezzi»;
  - nessuna media.
- **Diario**:
  - quello principale registra A1 con `model="A1"`;
  - FHS+VIX entra nel diario ombra (`shadow.py`) accanto a FHS, che oggi è senza VIX.
- **Coerenza**: la correzione `campioni.coerenza()` non serve più per mescolare motori. Resta solo come controllo: se A1 viola la monotonia tra orizzonti si mostra un avviso, senza alzare i numeri.
- **«Quanto fidarsi» → «Un motore per ogni orizzonte»**: diventa «Sfidanti in prova». Testo: «scelta fatta guardando la stessa valutazione: non è una prova; deciderà il diario dal vivo». Più una data di revisione descrittiva, **10 maggio 2027**, senza promozione automatica.
- `campioni.json` resta come tabella informativa.
- **Accettazione**: i numeri principali tornano quelli di A1; FHS+VIX è visibile ed etichettato; il diario registra entrambi; test verdi.

### Fase 1 — Verifica rigorosa e protocollo (patch 27) [solido]

**1a. Revisione del codice esistente**, con un rapporto scritto in `CONTINUA_DA_QUI.md`.
- Definizioni: `features.fwd_maxdd` = perdita massima rispetto al prezzo di oggi (non è il massimo drawdown). «10 giorni» = 7 sedute.
- Etichette e purge in `model.Engine.fit`, `modeleval`, `validate`, `ricerca`.
- Provenienza di `data/risk_history.csv`: deve essere walk-forward puro.
- Costruzione di `vwce_series()`:
  - livello / EURUSD;
  - VT con `auto_adjust=True` (rendimento con dividendi lordi, non netti come VWCE);
  - giunzione con VWCE.DE dal 23/07/2019.
- Ritardi in `fondamentali.LAG`.
- Pesi dell'Indice Armor scelti nel 2026 (adattamento a posteriori, da dichiarare).
- Dati FRED rivisti (non in tempo reale).
- Per ogni punto: «corretto / da correggere / limite da dichiarare». Gli errori trovati si correggono in questa patch, con un test.

**1b. Nuovo modulo `verifica.py`**, unico per tutti i modelli: stesse date, stessi esiti.
- Metriche: Brier, BSS rispetto alla frequenza storica nota a ogni data, log loss, AUC, curva di affidabilità a 10 classi, errore di calibrazione medio.
- **Finestre non sovrapposte**: per ogni orizzonte h, sottocampioni con una data ogni h sedute, per tutti gli h sfasamenti possibili. Si riporta la media e la dispersione tra sfasamenti.
- **Intervalli di confidenza con block bootstrap stazionario** (blocco medio = h sedute, 2.000 repliche) per BSS e per la differenza di Brier tra due modelli sulle stesse date.
- **Episodi**: eventi raggruppati per crisi (giorni con evento separati da meno di h sedute = stesso episodio). Si riporta il numero di episodi, non solo di giorni.
- **Test sulle differenze di perdita** (Diebold-Mariano con errori HAC, ritardo h−1) e correzione di Holm quando si confrontano più modelli.
- **PBO con CSCV**: matrice «configurazioni × blocchi di tempo» del Brier, dalle prove nel registro. Si riporta la probabilità che il migliore in campione sia sotto la mediana fuori campione.
- Per le distribuzioni (Fase 2): CRPS, copertura delle fasce 10-90 e 5-95. Per la volatilità: QLIKE.

**1c. Rifare la verifica** di A1, FHS, FHS+VIX, Indice Armor (trasformato in probabilità con logistica walk-forward) e «Solo prezzi» con `verifica.py`, 1994-oggi. Una tabella con intervalli di confidenza in «Quanto fidarsi», al posto dei BSS senza incertezza.

**1d. `PROTOCOLLO_VERIFICA.md`** (nuovo file, datato; il suo hash si scrive nel diario il giorno del rilascio).
- Cosa decide il diario dal vivo, con quali metriche e quale regola. Esempio di regola: differenza di Brier rispetto ad A1 con intervallo bootstrap al 90% tutto a favore dello sfidante.
- Il numero minimo di finestre indipendenti per decidere:
  - 1 mese: almeno 24 finestre mensili, cioè circa 2 anni;
  - 3 mesi o più: anni.
- Le revisioni intermedie già programmate (prima: 10 maggio 2027, solo descrittiva) e il divieto di guardare i risultati per decidere fuori da quelle date.
- Dichiarazione onesta: a 3-12 mesi la prova dal vivo richiede anni. Nel frattempo vale la verifica storica, con un controllo dal vivo «non peggiore».
- **Regola di adozione storica (per migliorare subito senza aspettare anni)**, da scrivere nel protocollo PRIMA di verificare il motore della Fase 2. A ogni orizzonte, una variante del motore diventa riferimento ufficiale al posto di A1 solo se, sulla verifica walk-forward 1994-oggi con `verifica.py`, valgono tutte queste condizioni:
  1. differenza di Brier rispetto ad A1 con intervallo bootstrap al 90% tutto a favore della variante, sia sul campione intero sia sui sottocampioni non sovrapposti (media degli sfasamenti);
  2. BSS positivo sia nel 1994-2012 sia nel 2013-oggi;
  3. pendenza di calibrazione tra 0,8 e 1,2;
  4. copertura della fascia 10-90 tra il 77% e l'83%;
  5. PBO sotto 0,5 tra le varianti provate.

  Si confrontano al massimo le varianti pre-registrate della Fase 2, con correzione di Holm. Se una variante passa, in app è etichettata «adottato sulla verifica storica, in conferma dal vivo». Se il diario dal vivo, alle date del protocollo, la mostra peggiore di A1 oltre l'intervallo di confidenza, si torna ad A1. Se nessuna variante passa, A1 resta e il motore resta sperimentale.

**Accettazione**: `verifica.py` testato con dati sintetici di cui si conosce il risultato (bootstrap, finestre non sovrapposte, episodi, PBO su configurazioni casuali ≈ 0,5); tabella in app; protocollo scritto e registrato.

### Fase 2 — Motore unico di percorsi (patch 28-29) [solido per la coerenza; ipotesi per l'accuratezza]

Nuovo modulo `percorsi.py`, basato su `fhs.py`.
- **Orizzonti**: 5, 21, 63, 126 e 252 sedute. I vecchi orizzonti (7, 21, 63, 126) restano nel diario storico; i nuovi hanno chiavi proprie.
- **Tre obiettivi dagli stessi percorsi**:
  1. rendimento finale: quantili 5-10-25-50-75-90-95 e P(rendimento < 0);
  2. perdita rispetto a oggi: P(minimo ≤ −5/−10/−15/−20%);
  3. massimo drawdown dentro il periodo: P(MDD ≤ −5/−10/−15/−20%), con il massimo calcolato lungo il percorso.

  Coerenza tra orizzonti e soglie per costruzione: niente più correzioni a mano.
- **Errore Monte Carlo**: 20.000 percorsi, stessi numeri casuali per tutti gli orizzonti (seme fisso per data). Per ogni probabilità l'errore standard √(p(1−p)/N) è salvato e mostrato quando supera 0,5 punti.
- **Persistenza ed emivita del GARCH** calcolate a ogni stima, registrate nel diario e mostrate in «Quanto fidarsi», con la curva della volatilità attesa giorno per giorno fino a 252 sedute.

**Varianti da confrontare** (pre-registrate; si sceglie con la verifica della Fase 1, mai a occhio).

Varianza nella parte iniziale:
- V0: FHS attuale;
- V1: FHS+VIX attuale (peso 0,5, premio 0,8);
- V2: struttura a termine: varianza media dei giorni 1-21 dal VIX, dei giorni 22-63 dalla varianza forward VIX/VIX3M. Entrambe moltiplicate per il rapporto «varianza realizzata / implicita» stimato in walk-forward (non 0,8 fisso). Oltre il giorno 63, la dinamica del GARCH. Provare a scaricare `^VIX6M` e `^VIX1Y` da Yahoo: se disponibili, estendere la curva.

Controllo delle code (necessario, §2):
- T1: tetto alla varianza condizionale (99,5° percentile delle varianze storiche filtrate);
- T2: ancoraggio di lungo periodo («FHS di lungo periodo»): dal giorno 63 la varianza viene riportata verso quella di lungo periodo con un vincolo di plausibilità;
- T3: blocchi storici di rendimenti riscalati per la volatilità (bootstrap filtrato a blocchi).

Criteri di scelta, in ordine:
1. copertura delle fasce e CRPS;
2. calibrazione di P(perdita) e P(MDD) a tutti gli orizzonti;
3. curtosi dei rendimenti a 126-252 sedute simile a quella storica;
4. a parità, la variante più semplice.

- **Verifica walk-forward** 1994-oggi, una data ogni 5 sedute, parametri rifatti ogni anno. Metriche con `verifica.py` sugli stessi giorni di A1.
- **In app**: il motore entra come «sperimentale» (o come riferimento, agli orizzonti in cui supera la regola di adozione storica della Fase 1d) nelle schede e in una nuova sezione «Scenari a 1 settimana - 1 anno» (fasce, probabilità di perdita e drawdown, P(fine in negativo) contro la frequenza storica). Diventa riferimento solo secondo il protocollo della Fase 1.
- **Accettazione**: coerenza verificata da test (P a 6 mesi ≥ P a 3 mesi; P(calo ≥20%) ≤ P(calo ≥10%)); code sotto controllo (nessun percorso oltre limiti dichiarati; curtosi misurata); tabella di verifica delle varianti nel registro.

### Fase 3 — VWCE in euro (patch 30) [solido]

- **Serie in euro con segmenti dichiarati** (`serie_eur.py`), mai uniti senza dirlo:

  | Segmento | Periodo | Note |
  |---|---|---|
  | (a) VWCE.DE reale | dal 23/07/2019 | Ad accumulazione, già in euro: nessuna conversione |
  | (b) VT rettificato per dividendi, convertito in euro | 2008-2019 | Livello / F(t), con F = dollari per euro: FRED DEXUSEU, oppure EURUSD=X di Yahoo |
  | (c) S&P 500 convertito in euro | dal 1999 | Solo per prove di robustezza, mai come «VWCE» |

  Limiti da dichiarare per il segmento (b):
  - VT segue il FTSE Global All Cap (comprende le piccole aziende), VWCE il FTSE All-World;
  - VT chiude alle 22:00, VWCE.DE alle 17:30: per confrontare le serie usare rendimenti settimanali;
  - ritenute fiscali diverse sui dividendi.

  Correlazione e differenza di rendimento tra i segmenti nel periodo in cui si sovrappongono (2019-oggi) riportate in «Quanto fidarsi».
- **Motore di percorsi stimato anche sui rendimenti di VWCE in euro** (dal 2008). L'S&P 500 in dollari resta il riferimento principale. Si verifica quale dei due prevede meglio gli esiti reali di VWCE in euro 2008-oggi (Fase 1).
- **Composizione reale**: provare a scaricare le partecipazioni e i pesi per paese dal sito Vanguard del fondo (file pubblico), archiviati con la data. Se non riesce, restano le stime etichettate «stima dalla capitalizzazione». Bassa priorità.
- **Accettazione**: segmenti visibili e documentati; test sulla conversione (un caso numerico con F noto); confronto S&P contro VWCE-euro nel registro.

### Fase 4 — Indice di affidabilità (patch 31) [solido]

Nessun punteggio con pesi inventati: segnali chiari con soglie fissate prima, mostrati uno per uno.

| Segnale | Quando si accende |
|---|---|
| Disaccordo | \|sfidante − A1\| ≥ 5 punti e rapporto ≥ 2 su una soglia principale |
| Dati vecchi | qualche serie chiave rossa in `salute.py` |
| Situazione mai vista | distanza di Mahalanobis dello stato di oggi (variabili di A1 + VIX + spread BAA + curva 10Y-3M) oltre il 99° percentile della storia di addestramento |
| Errori recenti | Brier delle ultime previsioni scadute nel diario peggiore della frequenza storica (attivo solo con almeno 12 finestre scadute) |
| Instabilità | la probabilità cambia di oltre 3 punti stimando il GARCH su finestre diverse (dal 1950, dal 1990, ultimi 15 anni) |

- **Livello**: 0 segnali = affidabilità alta; 1 = media; 2 o più = bassa, con l'avviso «stima poco affidabile: …» e le ragioni.
- **Accettazione**: test per ogni segnale; riquadro in Oggi accanto alle probabilità.

### Fase 5 — Simulatore del PAC (patch 32) [solido]

- **Dati inseriti dall'utente**, salvati solo nel browser:
  - capitale attuale e versamento mensile;
  - giorno di acquisto;
  - costo per acquisto;
  - costo annuo del fondo (TER), con valore predefinito da verificare sulla scheda Vanguard del fondo e modificabile.
- **Percorsi**:
  - primi 12 mesi dal motore condizionato (Fase 2, VWCE in euro, variante scelta);
  - oltre, bootstrap stazionario a blocchi dei rendimenti mensili storici in euro (non condizionato: dopo circa 63 sedute il GARCH ha già dimenticato lo stato di oggi e le code non sono affidabili).
- **Due scenari, sempre insieme**:
  - «storico»: rendimenti del campione;
  - «prudente»: gli stessi con 3 punti all'anno in meno.

  Avviso che il risultato dipende molto dal rendimento medio del campione.
- **Risultati a 1, 3 e 5 anni**:
  - percentili 5-10-25-50-75-90-95 del patrimonio;
  - probabilità che il patrimonio sia sotto i versamenti;
  - calo massimo del patrimonio accumulato.
- **Confronto «continuo il PAC / sospendo 3 o 6 mesi»**, con le due ipotesi per i soldi non investiti dette in chiaro: liquidità ferma, oppure investita tutta alla ripresa.
- **Messaggio per chi accumula**, in Oggi e nel simulatore: «Per chi accumula a rate, i cali dei primi anni comprano più quote; il rischio pesa di più vicino al momento in cui si disinveste». Non cambia soglie né probabilità; il simulatore non suggerisce mai di sospendere.
- **Accettazione**: test su un caso deterministico (rendimento costante → valore noto); nessun percorso oltre i limiti delle code; screenshot a 430px.

### Fase 6 — Esperimenti, sempre in ombra (patch successive)

- **6a. VRP corretto** [ipotesi].
  - Scaricare apertura/massimo/minimo/chiusura di `^GSPC` (dal 1990, come il VIX).
  - Varianza realizzata con lo stimatore Yang-Zhang (separa notte e seduta).
  - Varianza fisica attesa a 21 sedute = previsione ex ante (GARCH e, in alternativa, HAR sulla varianza Yang-Zhang).
  - VRP = (VIX/100)² − varianza attesa, nelle stesse unità.
  - Confronto con `verifica.py` di: solo VIX / FHS / FHS+VIX / FHS+VIX+VRP, per perdita, drawdown e P(fine in negativo). Si adotta solo se supera il protocollo.
- **6b. HAR-RV** come previsore alternativo della varianza dentro il motore [ipotesi]: valutato con QLIKE. Il LASSO multi-mercato solo dopo, se 6b aiuta.
- **6c. Interazioni con i regimi** [sperimentale]: le regole di 6a/6b condizionate ai tre regimi esistenti, con regola pre-registrata e correzione per le prove multiple.
- **Rinviati**:
  - hazard model, teoria dei valori estremi, PCA/fattori latenti, reti neurali, HMM;
  - variabili estratte da notizie con modelli linguistici (eventualmente solo per classificare notizie con fonte e data, valutate come le altre variabili).

### Fase 7 — Diario più completo (insieme alla Fase 2) [solido]

Nuovo diario `data/journal_v3.csv`, solo aggiunte e con catena di hash. Il diario attuale resta intatto. Una riga per data e modello, con:
- data e ora UTC, versione del codice (variabile `GITHUB_SHA`), nome e versione del modello;
- parametri (GARCH, seme, numero di percorsi, variante);
- valori delle variabili usate e data dell'ultimo dato di ogni serie;
- tutte le probabilità e i quantili, con l'errore Monte Carlo;
- esiti solo quando maturano, in righe separate.

`journal.verify()` esteso al nuovo file.

---

## 4. Ordine e cosa non fare

| Patch | Fase | Tipo |
|---|---|---|
| 26 | 0 — A1 riferimento, FHS+VIX sperimentale affiancato | solido, piccola |
| 27 | 1 — revisione + `verifica.py` + protocollo | solido |
| 28-29 | 2 + 7 — motore unico di percorsi con controllo delle code + diario v3 | solido / ipotesi |
| 30 | 3 — VWCE in euro | solido |
| 31 | 4 — indice di affidabilità | solido |
| 32 | 5 — simulatore PAC | solido |
| 33+ | 6 — VRP, HAR, regimi | ipotesi / sperimentale |

Da non fare:
- aggiungere indicatori nuovi per ora;
- cambiare il riferimento ufficiale senza il protocollo;
- usare il 2019-2026 come prova nuova;
- mostrare medie tra modelli;
- inserire cifre trovate in articoli senza verificarle sui dati;
- promettere che il modello diventerà «più preciso».

**Limite che resta.** La direzione del mercato resterà imprevedibile. Il risultato atteso del piano è avere:
- probabilità coerenti, con la loro incertezza esplicita;
- il rischio dell'investimento reale (VWCE in euro);
- un avviso quando la stima non è affidabile;
- scenari utili per il PAC.
