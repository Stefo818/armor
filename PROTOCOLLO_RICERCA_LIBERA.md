# Protocollo: ricerca libera di nuovi segnali di crisi finanziaria

Scritto e pubblicato PRIMA di calcolare qualsiasi risultato (23 novembre 2026). Nessuna regola viene cambiata dopo.

## Perimetro
Solo crisi di origine finanziaria (mercato troppo caro/esteso, tassi in salita, credito e liquidità che si stringono). Le finestre di shock esterno (guerre, Covid, dazi: lista ESTERNI di classifica_40anni.py, da -5 a +60 sedute) e le due crisi miste (-5/+180 sedute) sono escluse da tutti i calcoli, come nei test precedenti.

## Candidati (32, tutti nuovi rispetto ai 21 già provati; più alto = più rischio)
Valutazioni: D01 CAPE · D02 P/E · D03 Indice Buffett (ritardo 90 giorni) · D04 premio al rischio basso (−erp, ritardo 30).
Caro + qualcosa che peggiora: D05 CAPE × salita del rendimento a 10 anni (63 sedute) · D06 CAPE × stretta delle condizioni finanziarie (nfci, 13 settimane) · D07 CAPE × prezzo sotto la media a 200 giorni.
Condizioni finanziarie: D08 nfci livello · D09 nfci variazione 13 sett. · D10 nfci leva · D11 stlfsi · D12 kcfsi (ritardo 35) · D13 ciss.
Tassi e liquidità: D14 salita rendimento 10 anni (63 sedute) · D15 salita rendimento 2 anni (63) · D16 prosciugamento liquidità netta (−net_liq_13w) · D17 M2 annuo basso (−m2_yoy, ritardo 45) · D18 crescita fondi monetari a 63 sedute.
Struttura della volatilità: D19 MOVE · D20 VIX/VIX3M · D21 VVIX · D22 variazione VIX a 21 sedute.
Prezzi: D23 distanza sotto la media a 200 giorni · D24 momento a 10 mesi negativo · D25 rendimento a 252 sedute (esteso) · D26 distanza sopra la media a 200 giorni (esteso).
Credito: D27 HYG/IEF variazione 63 sedute (negativa = rischio) · D28 prestiti alle imprese, crescita annua in calo (ritardo 45) · D29 stretta dei prestiti SLOOS (ritardo 30) · D30 insoluti imprese (ritardo 60).
Misti semplici: D31 media dei punteggi D01, D08, D14 · D32 media dei punteggi D19, D23, D27.
Punteggio = percentile espanso (solo passato; minimo 252 osservazioni giornaliere o 60 mensili/trimestrali). Un candidato con meno di 5 anni di dati validi nel periodo di scelta è «non valutabile» e non entra nella soglia del caso.

## Bersagli e periodi
Calo massimo dei prossimi 5 / 21 / 63 sedute di almeno −3% / −5% / −8% rispetto al prezzo di oggi. Scelta: fino al 2014. Verifica: dal 2015.

## Regole (identiche a ELEMENTI_ESTERNI)
P1 (segnale utile da solo): AUC verifica ≥ 0,60, estremo basso IC90 per blocchi d'anno > 0,50, e AUC sopra la soglia del caso (95° percentile del migliore su tutti i candidati con bersagli mescolati per anno, 120 prove).
P2 (adozione): misto 0,8·rank(Indice crollo) + 0,2·rank(candidato) migliora l'AUC di almeno +0,01 sia in scelta sia in verifica su almeno 2 orizzonti su 3, senza peggiorare di più di −0,01 in nessun caso.
Esito: «Coerente con i casi osservati» se P1 o P2, altrimenti «Non coerente». Mai «provato». Si dichiarano i limiti (pochi episodi, serie corte).
Se qualcosa passa P2, entra come ingrediente a peso 0,2 dell'Indice crollo SOLO dopo un secondo controllo: la stessa regola ripetuta escludendo, uno alla volta, i 3 anni con più episodi.
