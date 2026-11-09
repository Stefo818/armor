# PROTOCOLLO «REGIME DI TENSIONE» — versione 1, datato 9 novembre 2026

Scritto **prima** di calcolare qualsiasi risultato sul periodo 2013–oggi (PIANO_ESPANSIONE Patch 43). Non cambia dopo aver visto i risultati. L'impronta di questo file va in `data/protocollo_regime_log.csv`.
Origine: osservazione dell'utente («quando l'Indice Armor resta stabilmente sopra 40/50 seguono cali graduali e nuovi minimi»). Un'analisi preliminare (Opus, 09/11/2026, 2000–2026, **senza** test fuori campione) ha trovato l'effetto concentrato nel 2000–2012. Questo protocollo serve a dire se regge fuori campione.

## Dati
- Indice Armor giornaliero dal 2000-01-03 (serie `armor_index`), chiusure S&P 500 (`sp500`). Esiti calcolati sull'S&P 500. Orizzonte 126 sedute.
- Scelta della variante su **2006–2012** (previsioni dal 2006: 5 anni di addestramento). **Una sola verifica** su **2013–oggi**. Date valutate ogni 5 sedute.

## Varianti (4, non se ne aggiungono)
- V1: minimo mobile a 20 sedute dell'indice ≥ 45. Variabile: min20/100. Condizione «attiva»: min20 ≥ 45.
- V2: media mobile a 60 sedute ≥ 45. Variabile: ma60/100. Condizione attiva: ma60 ≥ 45.
- V3 «Pressione accumulata»: P_t = Σ_{k≥0} λ^k · max(0, A_{t−k} − 40), λ = 0,97; Pn = percentile di P_t nella storia **fino a t** (espanding, ≥250 sedute). Variabile: Pn. Condizione attiva: Pn ≥ 0,80.
- V4: V3 con distanza dai massimi. d = clip(calo dal massimo a 252 sedute, 0, 30%)/30%. Variabili: Pn, d, Pn·d. Condizione attiva: Pn ≥ 0,80 e calo dal massimo ≥ 5%.

## Esiti (orizzonte 126 sedute dal giorno del segnale)
- (a) nuovo minimo: il minimo delle 126 sedute successive è sotto il minimo delle 126 precedenti (giorno t incluso).
- (b) **esito principale**: calo massimo ≥ 10% rispetto al prezzo del giorno (identico al bersaglio «6 mesi, −10%» del modello A1).
- (c) rendimento a 126 sedute < 0.
- (d) «calo graduale»: rendimento a 126 sedute ≤ −5% **e** volatilità realizzata dei 126 giorni sotto la mediana storica (nota a quella data: solo finestre concluse).

## Metodo
- Regressione logistica walk-forward: riaddestrata ogni 1° gennaio con le sole date il cui esito era noto (data ≤ fine anno precedente − 126 sedute), penalità L2 piccola (1e-3). Riferimento: frequenza storica nota a quella data (purged).
- Metriche: Brier skill score (BSS) contro la frequenza storica, AUC, con intervalli al 90% da bootstrap stazionario di Politis-Romano (blocco medio 126/5 ≈ 25 osservazioni, 2000 ripetizioni, seme fisso).
- **Aggiunge informazione rispetto ad A1?** Si confrontano, sull'esito (b), due regressioni walk-forward: [logit(p A1)] contro [logit(p A1) + variabili della variante]. Differenza di Brier (modello con variante − solo A1) con intervallo al 90%: serve intervallo tutto sotto 0. p di A1 = previsioni walk-forward di `modeleval.a1_preds` («6m», −10%).
- Episodi: inizio = prima volta che la condizione attiva scatta dopo almeno 60 sedute senza. Per episodio: durata, calo massimo, nuovo minimo sì/no, rendimenti a 126 e 252 sedute.
- Kaplan-Meier: tempo dall'inizio dell'episodio al primo prezzo sotto il minimo delle 126 sedute precedenti l'inizio; censura a 252 sedute o a fine dati.
- Robustezza: stessa regola (V1, con l'indice Armor americano) sugli esiti (a), (b), (c) di STOXX 50, Nikkei 225 e VWCE (serie VWCE disponibile). Descrittiva, non entra nella regola.

## Scelta della variante e regola di adozione
- Variante scelta: quella con BSS medio più alto sui quattro esiti nel 2006–2012; a parità (differenza < 0,005) la più semplice nell'ordine V1, V2, V3, V4.
- La variante scelta diventa **indicatore ufficiale** solo se nel 2013–oggi, per l'esito (b): BSS > 0 con estremo inferiore dell'intervallo al 90% > 0; aggiunge informazione rispetto ad A1 (intervallo della differenza di Brier tutto sotto 0); ha almeno **4 episodi** con condizione attiva nel 2013–oggi.
- Altrimenti resta **descrittivo**, con la scritta «non verificato fuori campione». Nessuna modifica di soglie dopo i risultati.
- In ogni caso parte il registro in ombra (`data/regime_ombra.csv`, una riga al giorno: indice, condizioni attive, stato) e viene confrontato con gli esiti a 126 sedute quando maturano.

## Limiti dichiarati
- Pochi episodi indipendenti (circa 12 dal 2000): i risultati sono un indizio. Giorni consecutivi sovrapposti: gli intervalli usano blocchi, ma restano larghi.
- L'indice Armor storico usa regole fissate oggi: nel passato alcune scelte sono note a posteriori (limite già dichiarato in PROTOCOLLO_VERIFICA.md).
- Ogni esecuzione è nel registro, anche se negativa.
