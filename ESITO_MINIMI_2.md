# Esito: Minimi riletto «continua a scendere» (25 novembre 2026)

Segue PROTOCOLLO_MINIMI_2.md (commit 5772f06, scritto prima dei calcoli). Script scratch/minimi_2.py, numeri in scratch/minimi_2_esito.json.

## Risultato in una riga
La lettura voluta dall'utente (1 = ha smesso di scendere, 100 = continua a scendere) **non è dimostrata**: non prevede se il ribasso continua meglio del caso. Verdetto: **Non coerente** con i casi osservati. Nell'app è mostrata comunque (scelta di prodotto) con l'avviso esplicito.

## Come è costruita
Minimi = minimo fra «Panico recente» (massimo a 63 sedute) e (100 − «Segni di svolta»). Alto solo se c'è stato panico E non c'è ancora svolta. Senza panico, o con svolta, è basso. Sono le stesse voci di prima, lette al contrario nella parte «svolta».

## Numeri (AUC in verifica dal 2013; soglia del caso = 95° percentile del migliore su 4)
| Perimetro e bersaglio | M1 (nuova lettura) | Indice crollo | Soglia del caso |
|---|---|---|---|
| Tutti i giorni, scende ancora ≥5% in 21 sedute | 0,58 [0,48–0,65] | 0,66 | 0,62 |
| Tutti i giorni, scende ancora ≥8% in 63 sedute | 0,56 [0,43–0,67] | 0,62 | 0,65 |
| Sotto stress, ≥5% in 21 sedute | 0,51 [0,35–0,71] | 0,49 | 0,74 |
| Sotto stress, ≥8% in 63 sedute | 0,49 [0,33–0,73] | 0,56 | 0,76 |
La semplice inversione del vecchio indice (M0) vale 0,49–0,59: caso.

## Il dato che pesa di più
Nei giorni sotto stress con Minimi ≥ 80 (9 giorni in verifica, quindi pochissimi) il mercato nelle 21 sedute dopo è **salito** in media del 14%, contro lo 0,8% dei giorni con Minimi ≤ 20. Cioè i picchi di panico senza segni di svolta sono stati, in quei pochi casi, vicini ai minimi, non lontani. Il contrario di ciò che il nome «continua a scendere» promette.

## Cosa si può dire all'utente
- Il numero dice **quanto panico c'è e se si vedono già segni di svolta**. Non dice quanto ribasso resta.
- Per sapere se un ribasso sta per iniziare, l'indice che anticipa meglio resta il Crollo (a pochi giorni).
- L'Indice Occasione (vecchia lettura, per le entrate extra) resta nella Bussola con il suo nome.

## Limiti
Pochi blocchi di stress (circa 8–11 indipendenti), giorni sovrapposti, bersagli fissati prima ma legati al prezzo dell'S&P 500.
