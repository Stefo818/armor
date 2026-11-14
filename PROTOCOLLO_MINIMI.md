# Protocollo «Minimi e lungo periodo» (scritto il 14 novembre 2026, PRIMA di vedere i risultati)

Scopo: aiutare chi fa un piano di accumulo su VWCE a capire (a) se il mercato è vicino a un **minimo** a una settimana, un mese, tre mesi e un anno e (b) in che **fase di lungo periodo** si trova (2, 3, 5, 8, 10, 15 anni), per non farsi sorprendere da un «decennio perduto». Non è una previsione certa e non è un consiglio. Indice di riferimento: S&P 500 (VWCE ha un indice mondiale simile, ma la storia lunga esiste solo per l'S&P 500).

Lezione dei quattro protocolli Titan+: con i dati pubblici è molto difficile battere FHS+VIX. Qui non si cerca un modello nuovo «più furbo»: si usa FHS+VIX (già in produzione) per rispondere a una domanda diversa, e si **misura onestamente** se le risposte sono affidabili. Dove non lo sono, l'app lo dice.

## Parte A. Minimi a 1 settimana, 1 mese, 3 mesi, 1 anno

Scale (sedute): 1 settimana = 5, 1 mese = 21, 3 mesi = 63, 1 anno = 252. Tolleranza t: 1%, 2%, 4%, 8% (circa mezza oscillazione tipica di quella scala).

- **Candidato**: il prezzo di oggi è al massimo t sopra il minimo delle ultime H sedute (cioè è vicino a un minimo già visto, o lo sta facendo).
- **Evento «minimo tenuto»** E: nelle H sedute successive il prezzo non scende più di t sotto quello di oggi.
- **Minimo di scala H** = candidato e E.
- **Previsione q**: probabilità di E calcolata con FHS+VIX (volatilità GJR-GARCH con errori storici pescati a caso, 1.500 percorsi, mezzo peso al VIX), rifatta con soli dati noti alla data (refit ogni 252 sedute, embargo 5). Date: una ogni 5 sedute dal 1990.
- **Calo residuo**: dai stessi percorsi, il calo massimo ulteriore al 50%, 80% e 95% (quanto può ancora scendere sotto il prezzo di oggi nelle H sedute).
- **Verdetto** per scala: «Minimo probabile» se candidato e q ≥ 0,75; «Possibile» se candidato e 0,55 ≤ q < 0,75; «Non ancora» negli altri casi (non candidato, o q < 0,55).
- **Calibrazione facoltativa** (una sola variante, scelta in anticipo): correzione a due parametri (termine fisso e pendenza sul logit di q), imparata in avanti (finestra espandibile, solo esiti maturati, almeno 150 casi candidati). Si adotta per una scala solo se riduce l'errore (Brier) sui giorni candidati nel periodo di taratura 1993-2012 **e** nel periodo di conferma 2013-2026 non è peggiore dell'0,5%. Altrimenti si usa q com'è.

### Prove (tutte dichiarate ora)
1. Giorni candidati: errore (Brier) di q contro la **frequenza storica dei candidati** (espansa, solo esiti maturati). Misura: risparmio % e intervallo al 90% (blocchi di 5). Superata per una scala se il risparmio è > 0 e l'intervallo esclude lo zero.
2. Taratura per fasce di q (<0,55, 0,55-0,75, ≥0,75): la frequenza reale di E deve crescere con la fascia e, nella fascia ≥ 0,75, non scostarsi da q di più di 10 punti.
3. Copertura del calo residuo: l'80% di calo residuo deve contenere la realtà in 74-86% dei giorni candidati.
4. Utilità (solo descrittiva): rendimento mediano a 1, 3 e 12 mesi dopo i giorni «Minimo probabile» contro tutti i giorni, e quante volte il verdetto sbagliava.
5. Divisione dei periodi: taratura 1993-2012, conferma 2013-2026 (già non guardata per queste domande). Si riportano anche le due metà separate.

Etichetta nell'app per ogni scala: **verificata** (prove 1-3 superate sia in taratura sia in conferma), **parziale** (alcune prove superate), **non verificata** (le altre). Il verdetto resta visibile, ma accompagnato dall'etichetta e dalla frequenza reale della fascia.

## Parte B. Lungo periodo: 2, 3, 5, 8, 10, 15 anni

Dati: S&P 500 mensile dal 1871 (prezzo, dividendi, prezzi al consumo: Robert Shiller) e CAPE mensile (prezzo diviso utili medi di 10 anni corretti per l'inflazione, serie `cape_m`). Rendimento = rendimento totale reale (dividendi reinvestiti, al netto dell'inflazione), annualizzato.

- **Modello**: y_h = a + b · ln(CAPE) per ogni orizzonte h, minimi quadrati, imparato **in avanti**: per prevedere a una data si usano solo coppie la cui finestra è già conclusa a quella data. Prima previsione nel 1920.
- **Fascia**: quantili 10%, 50%, 90% dei residui storici già noti a quella data, sommati alla previsione.
- **Probabilità di perdita reale** su h anni: quota dei residui (già noti) che porta il rendimento previsto sotto zero. «Decennio perduto» = rendimento reale su 10 anni sotto zero.
- **Fase di lungo periodo** (soglie fissate ora, sul percentile del CAPE rispetto alla sola storia nota a quella data): sotto il 60° = «Espansione sana»; 60°-85° = «Maturità: valutazioni care»; sopra l'85° = «Rischio di contrazione lunga».
- **Anni simili**: i mesi passati con CAPE entro ±15% da quello di oggi, raggruppati per episodio, con rendimenti reali a 5, 10 e 15 anni.

### Prove
1. Per ogni orizzonte: R² fuori campione contro la media storica nota alla data (positivo = il CAPE aiuta). Dichiarato come stimato con finestre sovrapposte: i casi indipendenti sono circa (anni di storia ÷ h), quindi pochi; la fiducia è comunque limitata.
2. Stabilità: segno e dimensione della pendenza b nelle due metà (1920-1969 e 1970-2023).
3. Taratura delle fasce: nella fase «Rischio di contrazione lunga» il rendimento reale mediano a 10 anni deve essere più basso che nelle altre fasi, in entrambe le metà.
4. Copertura della fascia 10%-90%: deve contenere la realtà in 70-90% dei casi.

Etichetta per orizzonte: **buona** (R² > 0,10 in entrambe le metà), **media** (R² > 0 in entrambe), **debole** (le altre). Il CAPE spiega bene i rendimenti a 10-15 anni e poco quelli a 2-3: lo si dice chiaramente nell'app.

## Regole generali
Nessun numero (soglie, tolleranze, pesi) si cambia dopo aver visto i risultati. Se una prova non è superata, l'app lo dichiara e non nasconde il risultato. L'impronta di questo file è salvata quando il lavoro giornaliero parte.


---
# Aggiunta del 14 novembre 2026 (scritta PRIMA di vedere i risultati delle parti C-G)

## Parte C. Radar dei minimi in euro
Serie: VWCE in euro (VT convertito in euro fino al 29/07/2019, poi VWCE.DE reale: `serie_eur`, segmenti dichiarati). Stesse scale, tolleranze, soglie (0,75 / 0,55), stesso modello (FHS+VIX, mezzo peso al VIX) e stesse prove della parte A. Date: una ogni 5 sedute dal 2011-01. Divisione dei periodi: taratura fino al 31/12/2018, conferma dal 2019. Etichetta con la stessa regola. Limite dichiarato: serie più corta (circa 18 anni), quindi meno casi.

## Parte D. Tipo di ribasso (descrittiva)
Distanza dal massimo storico (chiusure S&P 500, dal 1928): sotto 5% «vicino ai massimi»; 5-10% «calo normale»; 10-20% «correzione»; 20-30% «mercato orso»; oltre 30% «crisi». Per ogni fascia: calo ulteriore massimo (mediana e 80%) nelle 63 e 252 sedute successive, probabilità che il calo ulteriore superi il 10% in 252 sedute, rendimento mediano a 12 mesi. Giorni sovrapposti, quindi pochi episodi indipendenti: nessuna prova di capacità previsiva, solo contesto.

## Parte E. Lungo periodo con i tassi (variante B)
Variante A (in uso): y = a + b·ln(CAPE). Variante B: y = a + b·ln(CAPE) + c·(tasso a 10 anni meno inflazione sui 12 mesi), stesso metodo in avanti. B sostituisce A per un orizzonte (5, 8, 10, 15 anni) solo se il suo R² fuori campione supera quello di A di almeno 0,02 sia in 1920-1969 sia in 1970-2023 (per B il primo anno utile dipende dai dati sui tassi, dal 1953 circa: la prima metà è quindi 1960-1969). Altrimenti resta A e la pagina lo dice.

## Parte F. Altri mercati (descrittiva)
Per S&P 500, Nikkei 225, DAX, FTSE MIB (indici di prezzo, valute locali): calo massimo dal picco e durata più lunga sotto il massimo precedente (anni). Nessuna prova: serve a ricordare che il «decennio perduto» non è solo americano.

## Parte G. Pagella in tempo reale e «Cosa fare oggi»
Pagella: ogni giorno si salvano verdetto e q delle 4 scale; a maturazione (H sedute) si registra se il minimo ha tenuto. Si riportano numero di casi, frequenza reale e q media per verdetto; nessuna etichetta prima di 30 casi maturati.
«Cosa fare oggi» (regole fisse, senza importi): versamento programmato = sempre «continua»; extra = «occasione forte» se almeno una scala tra 1 mese, 3 mesi e 1 anno è «probabile»; «occasione debole» se solo la settimana è «probabile» o se c'è almeno un «possibile»; altrimenti «nessuna occasione». Con fase «Rischio di contrazione lunga» la forza «forte» richiede «probabile» a 3 mesi o 1 anno, altrimenti diventa «debole». Cautela = la più alta tra: regime di tensione (calma/normale = bassa, formazione = media, persistente = alta), fase di lungo periodo (sana = bassa, cara = media, contrazione = alta, a meno che l'occasione sia forte) e distanza dal massimo (oltre 10% = alta).
Avvisi sul telefono: un messaggio solo quando una scala diventa «probabile» (dal giorno prima non lo era) o cambia la fase di lungo periodo.


---
# Aggiunta del 14 novembre 2026, parte 2 (scritta PRIMA di vedere i risultati delle parti H-K)

## Parte H. Crescita in tempo reale
Fonti: GDPNow della Fed di Atlanta (FRED: GDPNOW, stima della crescita del trimestre in corso, annualizzata) e crescita reale ufficiale (FRED: A191RL1Q225SBEA). Prova di accuratezza: per ogni trimestre già pubblicato dal 2011, errore assoluto medio di GDPNow contro un metodo ingenuo (crescita del trimestre precedente), e quota di trimestri con segno giusto (sopra/sotto zero). GDPNow è «utile» se l'errore è minore di quello ingenuo; altrimenti l'app lo dice. Semaforo di crescita (regole fisse): verde = stima almeno 1,5% e indicatore di Sahm sotto 0,3 e probabilità di recessione sotto 20%; rosso = stima sotto 0% oppure Sahm almeno 0,5 oppure probabilità di recessione almeno 40%; giallo = tutti gli altri casi. Descrittivo: rendimento mediano dell'S&P 500 a 3 mesi dopo ogni fascia di stima (dal 2011).

## Parte I. Stress test e perdita massima
Crisi storiche (da massimo a minimo di chiusura): bolla internet (2000-03 → 2002-10), crisi finanziaria (2007-10 → 2009-03), Covid (2020-02-19 → 2020-03-23), tassi e inflazione (2022-01 → 2022-10), crollo del 1987, 1973-74, 1929-32. Per le crisi dal 2008 si usa il VWCE in euro (serie a segmenti dichiarati), per le precedenti lo S&P 500 in dollari (indicato). Per ciascuna: calo massimo, giorni fino al minimo, giorni per tornare al massimo e effetto su un piano di accumulo mensile costante (quota del versato a minimo e dopo 3 anni dal massimo). Perdita attesa: simulazione FHS+VIX sul VWCE in euro (3000 percorsi), a 1, 3 e 12 mesi: perdita superata solo nel 5% e nel 20% dei casi, perdita media nel peggior 5% (expected shortfall), calo massimo lungo il percorso a metà/4 su 5/19 su 20 dei casi. Prova: la frequenza reale (storia del VWCE in euro dal 2011, date ogni 5 sedute) con cui la perdita a 3 mesi ha superato la soglia del 5% deve stare tra 3% e 8%; altrimenti si dichiara.

## Parte J. Trend e momentum
Segnali sull'S&P 500 (chiusure, dal 1928), calcolati a fine giornata e applicati dal giorno dopo: T1 = chiusura sopra la media semplice a 200 sedute; T2 = rendimento da 252 a 21 sedute fa positivo (momentum «12 meno 1 mese»); T3 = media a 50 sedute sopra quella a 200. Punteggio = numero di segnali positivi (0-3). Strategia di prova per ciascun segnale e per il punteggio ≥ 2: in mercato quando il segnale è positivo, altrimenti in liquidità al tasso a 3 mesi dei titoli di Stato USA (tb3ms); senza costi né tasse (dichiarato); indice di prezzo senza dividendi (dichiarato: sottostima mercato e strategia). Misure: rendimento annuo, calo massimo, volatilità, quota di tempo investito, cambi di segnale all'anno; su 1928-1977, 1978-2026 e tutto. Etichetta: «protegge» se il calo massimo si riduce di almeno un quarto in entrambe le metà; «rende di più» se il rendimento annuo supera quello di comprare e tenere in entrambe le metà. Descrittivo: rendimento a 3 e 12 mesi e probabilità di un calo ulteriore oltre 10% dopo ogni punteggio.

## Parte K. Flussi e posizionamento
Termometro di affollamento: media di percentili (storia nota fino a quella data, finestra espandibile, minimo 3 anni) di: posizione netta dei fondi speculativi sui futures (COT), debito per comprare titoli (variazione annua, FINRA), liquidità nei fondi monetari (variazione annua; invertita), indice SKEW, struttura a termine del VIX (VIX/VIX a 3 mesi, invertita) e, se aggiornato, differenza rialzisti-ribassisti AAII. Più alto = mercato più affollato e compiacente. Prova: dal 2011, rendimento a 3 mesi dell'S&P 500 e probabilità di calo oltre 7% in 3 mesi per fasce del termometro (sotto 20%, 20%-80%, sopra 80%): utile solo se il calo è più frequente sopra l'80% che sotto il 20% con intervallo al 90% (blocchi) che esclude zero. Opzioni su SPY (dati correnti di Yahoo, nessuna storia): rapporto put/call sugli interessi aperti, muro di call e di put (strike con più interessi aperti), gamma netta stimata e livello di cambio di segno, con l'ipotesi dichiarata che gli operatori abbiano venduto call e comprato put. Nessuna prova possibile oggi: ogni giorno si registra il dato e dopo almeno 60 giorni si confronta il movimento assoluto del giorno dopo con gamma positiva e negativa. Nessun numero si cambia dopo aver visto i risultati.

### Chiarimenti scritti prima della consegna (solo su disponibilità dei dati)
- Stress test: le crisi 2000-02 e 2008 usano l'S&P 500 convertito in euro, perché i dati del fondo mondiale (VT) iniziano a giugno 2008. La prova della simulazione riguarda il calo massimo (soglie 80% e 95%), non la perdita finale.
- Le opzioni su SPY non hanno storia scaricabile: il diario parte dal primo giorno di raccolta e la verifica scatta dopo 60 giorni.
