# Protocollo: Crollo × Stato, incrociarli aiuta? (25 novembre 2026)

Scritto PRIMA di calcolare qualsiasi risultato. Nessuna regola cambia dopo; l'esito si pubblica anche se negativo.

## Domanda dell'utente
In un terreno fragile (Stato alto) il crollo per cause interne è più probabile. Incrociando Crollo e Stato si ottiene un segnale migliore del Crollo da solo?

## Dati
Serie giornaliere dal 1990: Crollo (versione 2, senza distanza dal massimo) e Stato (media delle 10 voci di fragilità, scala 1–100), da status_index.py. S&P 500.

## Punteggi misurati (5, fissati ora)
- **X0** Crollo da solo (riferimento), media a 5 sedute.
- **X1** Stato da solo.
- **X2** prodotto: (Crollo5 / 100) × (Stato / 100) × 100.
- **X3** minimo fra Crollo5 e Stato («servono tutti e due»).
- **X4** regola a due livelli: Crollo5 > 60 E Stato > 60 (punteggio 1/0).
Nessuna ottimizzazione di soglie o pesi.

## Bersagli
- **B1** il minimo dei 5 giorni successivi scende ≥ 3% sotto la chiusura di oggi (come la «settimana a rischio»).
- **B2** il minimo dei 21 giorni successivi scende ≥ 8% (cade più a lungo, tipico dei terreni fragili).
Perimetro come PROTOCOLLO_SFASATO: solo crisi finanziarie (esclusi gli shock esterni di classifica_40anni: ESTERNI e MISTE_MAX con le stesse finestre di crollo_v2_regola.py).

## Misura
AUC. Scelta: fino al 2014. Verifica: dal 2015. Intervallo al 90%: bootstrap per anno (500). Soglia del caso: 95° percentile del migliore AUC di verifica fra i 5 punteggi con bersagli mescolati per anno (200 prove). Per X4 anche: frequenza del bersaglio nei giorni accesi contro la base, in verifica; episodi = giorni accesi separati da più di 21 sedute (per B1) / 63 (per B2).

## Criterio
Adottato nel Crollo solo se un punteggio X1–X4 supera X0 in verifica con intervallo al 90% che non include la differenza zero e supera la soglia del caso, per entrambi i bersagli. Altrimenti resta un'informazione separata, peso zero. Verdetti: «Coerente con i casi osservati» / «Non coerente».
