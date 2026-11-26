# Esito giro 2: Crollo che si alza prima dei picchi (26/11/2026)
Protocollo: PROTOCOLLO_CROLLO_V3B.md (commit 5762945). Script: scratch/crollo_v3b.py; dati: scratch/crollo_v3b_esito.json. Soglia del caso (AUC su Yp, 2015+): 0,726.

## Risultato: nessun candidato passa (vincitore in scelta: Q2, alberi su F1 mescolati al vecchio; passa solo il criterio ii)
- Modelli addestrati solo sul picco in arrivo (P1-P4): AUC su Yp 0,61-0,65 contro 0,41 del vecchio, ma sotto la soglia del caso (0,726) e senza capacita' di separare i giorni rischiosi (AUC su Yb 0,41-0,49, il vecchio 0,82). Stacco prima dei picchi tra -1,8 e +2,0: nessun guadagno reale.
- Mescolati al vecchio (Q1-Q4): tengono la separazione dei giorni rischiosi (rapporti 2,5-4,6) ma l'AUC sul picco torna a 0,49-0,51 (caso).
- Stacco prima dei 5 picchi 2018-2024: mai oltre +2,0 (serve +5 sul vecchio, -2,3).

## Conclusione
Con tutte le fonti oggi disponibili (12 famiglie, parti di Gemini, VIX9D, VVIX, CISS, titoli di Stato europei, Fama-French, dispersione dei settori) e due modi di insegnare il bersaglio, la ricerca non trova un indice che si alzi in modo affidabile nei 10 giorni prima di un picco e resti utile sui giorni rischiosi. I picchi 2018-2024 partono da mercati calmi. L'unico segnale vero e veloce resta la reazione (pochi giorni dopo l'inizio), non l'anticipo.
