# Esito: «Difensività dei grandi fondi» (24/11/2026)
Regole: PROTOCOLLO_DIFENSIVITA.md (commit 2288168), una sola esecuzione (`scratch/difensivita.py`, risultati in `scratch/difensivita_esito.json`). 8 prove sul test T1 (soglia del migliore fra 8: DR 0,227).

## Verdetto
- **H1 «i fondi diventano difensivi prima del calo»: non supportata.** DIF-L alto (≥ 0,80): DR +0,03 e +0,01 sul calo −8% (IC90 include 0 in entrambi i blocchi); sul −12%, −0,03 dopo il 2015. DIF-C alto (completo, con COT, obbligazioni e 13F): +0,35 fino al 2014 (IC90 0,16–0,52, 6 episodi), **+0,006 dal 2015**: non regge.
- **T2 (rimbalzo dopo un calo ≥ 10%): non utile.** Dal 2015 non esiste nessun giorno con difensività bassa (n = 0): non valutabile; prima del 2015 differenza −5,4 punti con IC90 da −9 a +13.
- **T3 (strato di conferma con Bolla o Credito ≥ 70): nella direzione scritta non utile.** Con Bolla o Credito accesi e fondi *poco* difensivi, il calo −8% in 63 sedute è arrivato nel **5,3%** dei casi; con fondi *molto* difensivi nel **20,6%** (DR −0,15, IC90 −0,25/−0,07; −0,16 prima del 2015, −0,12 dopo con IC90 −0,26/+0,002). Il segno è l'opposto di quello che il protocollo definiva «utile»: la direzione, in senso H1, c'è ma come osservazione dopo il calcolo.

## Cosa c'è di vero, e la cautela
Un solo fatto è stabile in tutte le prove: **quando i fondi sono poco difensivi (DIF-L ≤ 0,20) il calo è molto meno frequente** (−8%: 6% contro 18% fino al 2014; 0% contro 13% dal 2015; −12%: 2% contro 11% e 0% contro 5%; IC90 sotto zero in tutti e quattro i casi). Ma non è «i grandi fondi sanno qualcosa»: l'indice misura anche quanto sono saliti i prezzi (la liquidità cresce meno del mercato, l'oro non batte le azioni) e quindi coincide in buona parte con il **momentum**: dopo salite robuste i cali a tre mesi sono più rari. Non è stato provato che aggiunga qualcosa all'Indice crollo.
Alla domanda dell'utente: **la liquidità e le obbligazioni dei fondi non anticipano il crollo**; quando i fondi sono molto difensivi, è un segnale che il rischio è già in corso, non che stia per arrivare.

## Oggi (23/11/2026)
DIF-L 0,22 (poco difensivi) e DIF-C 0,39. Componenti: fondi monetari 0,34, oro contro azioni 0,02, obbligazioni lunghe contro azioni 0,80, fondi a leva 0,49, gestori patrimoniali 0,13, protezioni 13F 0,73. Dati dei fondi monetari fermi al 05/10/2026.

## Cosa entra nell'app
Nulla di visibile (nessun test è «dimostrato/utile»). Solo il registro giornaliero `data/difensivita_registro.csv` (peso zero) per verificare in avanti. Un'eventuale prova che l'indice aggiunge informazione oltre al momentum richiede un nuovo protocollo.
