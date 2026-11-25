# Protocollo: la correlazione aiuta a riconoscere un minimo? (25 novembre 2026)

Scritto e pubblicato PRIMA di calcolare qualsiasi risultato. Nessuna regola cambia dopo.

## Domanda dell'utente
Il video di Marco Casario mostra l'indice di correlazione implicita (COR1M) e l'utente chiede se, abbinato ai modelli di Armor, aiuta a capire quando si è raggiunto un minimo. Lo storico di COR1M e COR3M non è disponibile (3 giorni nell'archivio). Si usa come sostituto una **correlazione effettiva dei settori**: media delle correlazioni a coppie fra i rendimenti giornalieri dei nove settori (sec_xlk, xlf, xlv, xly, xli, xlp, xle, xlu, xlb) in 21 sedute (C21). Storia dal 1999. È un sostituto dichiarato, non è COR1M: misura la correlazione realizzata, non quella attesa dalle opzioni. Controllo descrittivo, dal 2015: stessa lettura con d_correlazione_media_21 (titoli dell'S&P 500, con possibile errore di selezione).

## Il modello di riferimento
L'Indice Occasione di Armor (occasione.py): Svolta (5 voci) e Panico (5 voci), Occasione = minimo fra Panico recente (massimo a 63 sedute) e Svolta.

## Punteggi misurati (8, fissati ora)
- **R0** Occasione (riferimento). **R1** Svolta (riferimento).
- **K1** «correlazione che rientra», da sola: 100 × clip(−(C21 / massimo di C21 nelle 63 sedute − 1) / 0,25, 0, 1), valida solo se il massimo di 63 sedute di C21 è oltre il suo 90° percentile storico (espanso, solo passato); altrimenti 0.
- **K2** «correlazione alta», da sola: percentile espanso di C21 × 100.
- **K3** Svolta a 6 voci (le 5 attuali + K1) e Occasione con quella Svolta.
- **K4** Panico a 6 voci (le 5 attuali + K2) e Occasione con quel Panico.
- **K5** K3 + K4 insieme.
- **K6** Svolta a 6 voci (K3) da sola.
Le voci aggiunte hanno lo stesso peso delle altre (media semplice, nessuna ottimizzazione).

## Giorni e bersagli
Giorni «sotto stress»: S&P 500 almeno l'8% sotto il massimo a 252 sedute. Tutti i giorni, senza escludere shock esterni (per i minimi non conta la causa). Due bersagli, entrambi «il minimo ha tenuto»:
- **T1** il minimo delle 21 sedute successive non è sceso più del 3% sotto la chiusura di oggi.
- **T2** il minimo delle 63 sedute successive non è sceso più del 5% sotto la chiusura di oggi.
Misura: AUC (alto = più probabile che il minimo regga). Scelta: 1999-2012. Verifica: 2013-2026. Episodi indipendenti = giorni con bersaglio separati da più di 63 sedute. Se in verifica i giorni sotto stress formano meno di 6 episodi, il bersaglio non è valutabile.
Intervallo al 90%: bootstrap per anno (500 ripetizioni). Soglia del caso: 95° percentile del migliore AUC di verifica fra gli 8 punteggi, con bersagli mescolati per anno (200 prove).

## Descrittivo: il picco di correlazione e il minimo
Per ogni discesa di almeno 12% dal massimo a 252 sedute (da massimo a minimo di chiusura, separate da almeno 126 sedute): data del minimo di prezzo, data del picco di C21 nella discesa, distanza in sedute, e valore di C21 al minimo contro la sua mediana. Si riporta quante volte il picco di C21 cade entro ±10 sedute dal minimo. Nessuna prova: serve a capire se la correlazione si accende al momento giusto o in ritardo.

## Regole di accettazione
Un punteggio K sostituisce o integra l'Occasione solo se, rispetto a R0:
- **B1** AUC(K) ≥ AUC(R0) + 0,03 sia in scelta sia in verifica, su T1 e su T2;
- **B2** AUC verifica di K sopra la soglia del caso (migliore di 8) su almeno un bersaglio;
- **B3** limite inferiore dell'intervallo al 90% in verifica sopra 0,55.
Se nessuno passa, l'Occasione resta com'è e si dice che la correlazione non migliora il riconoscimento dei minimi con questi dati. Esito: «Coerente con i casi osservati» / «Non coerente»; mai «provato». Se un punteggio ha segno stabile ma non passa, è un indizio (registro in avanti). Quando avremo almeno due anni di COR1M e COR3M reali, la stessa prova si ripete con quelli.
