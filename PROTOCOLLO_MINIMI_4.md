# Protocollo: Minimi su molti mercati insieme (25 novembre 2026)

Scritto PRIMA di calcolare. Seguito di PROTOCOLLO_MINIMI_3 (nessun modello su S&P 500 solo ha funzionato: troppo pochi episodi di crollo, circa 8–11 indipendenti). Qui si allarga l'esempio: gli stessi modelli e le stesse regole, ma addestrati e misurati su 13 mercati insieme.

## Mercati (dai dati già salvati, storia dal 1990 circa)
S&P 500 (unico indice USA), FTSE 100, CAC 40, SMI, IBEX, AEX, BEL 20, Hang Seng, Toronto, Sydney, San Paolo, Seul, Taiwan, Messico: 13 mercati, ma se uno ha meno di 15 anni di storia entra comunque dal suo primo anno utile (almeno 1.500 giorni).

## Variabili
Solo di prezzo (le stesse 13 del Protocollo 3), calcolate per ogni mercato; paura e credito non esistono per tutti, quindi non entrano.

## Bersagli e perimetro
Stessi F1 (scende ancora ≥5% in 21 sedute) e F3 (sale e non scende oltre il 2% in 21 sedute). Giorni «sotto stress» di un mercato: ≥8% sotto il suo massimo a 252 sedute.

## Modelli (3, configurazioni fisse come nel Protocollo 3)
- **H1** logistica (C=0,1) su tutti i giorni di tutti i mercati.
- **H3** logistica solo sui giorni sotto stress.
- **H5** alberi potenziati (profondità 2, 100 alberi, passo 0,05) su tutti i giorni.
Scorrimento annuale: per l'anno Y addestramento sui dati fino a Y−1 meno 63 giorni, di tutti i mercati; previsione di Y per tutti i mercati. Previsioni dal 2000 (tutte fuori campione).

## Misura
AUC su F1 e F3 invertito, giorni sotto stress, tutti i mercati insieme; bootstrap per anno (500) per l'intervallo al 90%; soglia del caso = 95° percentile del migliore dei 3 modelli con bersagli mescolati per anno entro mercato (200 prove). In più: AUC per mercato (quanti mercati su 13 sopra 0,5) e rendimento medio a 21 sedute con punteggio ≥ 80 (percentile espanso delle previsioni passate nel mercato) contro ≤ 20.

## Criterio
Come nel Protocollo 3: servono (a) AUC F1 sopra la soglia del caso con limite inferiore IC90 > 0,5; (b) AUC F3 con limite inferiore IC90 > 0,5; (c) rendimento con punteggio ≥ 80 inferiore a quello con ≤ 20; (d) almeno 10 mercati su 13 con AUC F1 > 0,5. Se passa, si studia come usarlo sull'S&P 500 con un secondo protocollo prima di mostrarlo nell'app.
