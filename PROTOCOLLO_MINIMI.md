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
