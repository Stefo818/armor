# Esito: «Indice crollo 2», 16 punteggi a confronto (25 novembre 2026)

Protocollo: PROTOCOLLO_INDICE_CROLLO_2.md (commit dcf7bd8, scritto prima dei calcoli). Script: scratch/indice_crollo_2.py. Dati: scratch/indice_crollo_2_esito.json. Nessuna regola cambiata dopo i numeri.

## Cosa è stato misurato
Giorni di «partenza da fermo» (mercato vicino ai massimi e senza calo nei 5 giorni), solo crisi finanziarie. Scelta fino al 2014, verifica dal 2015. Tre eventi: E1 calo del 3% nei 5 giorni dopo, E2 calo del 5% fra 6 e 21 giorni, E3 calo dell'8% fra 22 e 63 giorni. Episodi indipendenti in scelta/verifica: E1 47/13, E2 30/8, E3 12/3 (E3 non valutabile in verifica).
16 punteggi: le 4 varianti dell'utente (V1 attuale, V2 senza distanza dal massimo, V3 con CAPE, V4 senza distanza e con CAPE) e 6 idee nuove dalla letteratura, ognuna da sola e mescolata 50/50 con l'indice attuale. Il controllo di coerenza conferma che V1 coincide con l'indice dell'app (correlazione 1,000).

## Risultati (AUC: 0,5 = caso, 1 = perfetto)
E1 (giorni dopo), soglia del caso «migliore di 16» = 0,694:
| punteggio | scelta | verifica |
|---|---|---|
| V1 attuale | 0,673 | 0,759 |
| V2 senza distanza dal massimo | 0,679 | 0,764 |
| V3 attuale + CAPE | 0,669 | 0,762 |
| V4 senza distanza + CAPE | 0,674 | 0,768 |
| N4 salita eccessiva con volatilità (misto) | 0,679 | 0,769 |
| N1 credito e prezzi insieme (da solo) | 0,654 | 0,538 |
| N5 terreno fragile × innesco (da solo) | 0,501 | 0,664 |
| N6 stretta di liquidità e tassi (da solo) | 0,593 | 0,516 |
| N2, N3 (da soli) | sotto 0,5 in scelta | 0,54 / 0,39 |

E2 (settimane dopo), soglia del caso 0,775: nessun punteggio la supera (migliore: N2 misto 0,733, N6 misto 0,728, N2 da solo 0,717 ma con scelta 0,43: segno opposto). Le varianti V1-V4 stanno tra 0,65 e 0,67.

## Regole
Nessuno passa A1 (+0,03 su E1 in entrambi i periodi). I migliori guadagni sono +0,006 (scelta) e +0,009 (verifica), ben dentro il rumore (intervalli al 90% larghi 0,17). **Resta l'Indice crollo attuale.**

## Cosa si impara
1. **L'indice attuale non è solo un termometro del presente**: da giorni calmi anticipa i cali dei 5 giorni successivi con AUC 0,76 in verifica, sopra la soglia del caso (0,694). L'anticipo c'è, è moderato.
2. **Togliere la distanza dal massimo (richiesta dell'utente) non peggiora e non migliora in modo misurabile** (+0,005 su E1; E2 +0,006 / +0,014). L'argomento logico è giusto (si accende dopo il calo), ma i dati non riescono a distinguerlo dal caso.
3. **Il CAPE, da solo o nell'indice, non aggiunge anticipo a 5 giorni** (V3 −0,004 / +0,003). Conferma ESITO_RICERCA_LIBERA.
4. **Le 6 idee nuove non battono l'indice attuale a pochi giorni.** Idee solide in letteratura (credito+prezzi, credito che si rovina, calma+caro, salita eccessiva) funzionano su orizzonti di anni e su crisi bancarie in decine di paesi, non su un calo del 3% in una settimana di un solo mercato.
5. **Indizio da seguire in avanti** (non adottato): N6 «stretta di liquidità e tassi» e N5 «terreno fragile × innesco» mostrano AUC 0,70-0,70 su E2 e 0,78-0,84 su E3 in verifica, con segno coerente in scelta per N6 (0,577), ma sotto la soglia del caso e con soli 8 e 3 episodi. Vanno nel registro per la prova in avanti, non nell'indice.

## Limiti
Pochi episodi in verifica (13, 8, 3). Soglia del caso con 200 prove. Per costruzione le idee nuove usano pesi fissati (nessuna ottimizzazione). Un indice con CAPE o senza distanza dal massimo può comunque essere scelto dall'utente per motivi di logica, ma non è dimostrato migliore.
