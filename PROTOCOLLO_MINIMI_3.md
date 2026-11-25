# Protocollo: un modello che dica se il mercato «continua a calare» o «ha toccato il minimo» (25 novembre 2026)

Scritto PRIMA di calcolare. Nessuna regola cambia dopo; l'esito si pubblica anche se negativo.

## Richiesta dell'utente
Un modello che capisca quando il mercato tende ancora a calare (valore alto, rosso) e quando ha raggiunto un minimo e tende a crescere (valore basso, verde). Si possono cambiare pesi, valori, calcoli, algoritmo.

## Dati e disciplina
Tutto noto alla chiusura del giorno (nessuno sguardo al futuro). Prove **a scorrimento annuale**: per ogni anno Y il modello si addestra solo sui dati fino a Y−1 (esclusi gli ultimi 63 giorni, perché i bersagli guardano avanti) e prevede l'anno Y. Così ogni previsione è fuori campione. Serie prezzo: S&P 500 dal 1950 (previsioni dal 1975 con le variabili di solo prezzo; dal 1999 con paura/credito/settori). Nessuna ottimizzazione di parametri: configurazioni fissate qui sotto.

## Variabili (fissate ora)
- **Prezzo (P)**: distanza dal massimo a 252 e a 63 sedute; rimbalzo dal minimo a 63 sedute; sedute dal minimo a 63 (max 63); rendimenti a 5, 21 e 63 sedute; prezzo/media a 50 e a 200 sedute; pendenza della media a 50 (21 sedute); volatilità realizzata a 21 sedute e suo rapporto con quella a 63; numero di sedute con calo oltre l'1% nelle ultime 21.
- **Paura e credito (V)**, dal 1999: livello della paura (VIX) in percentile storico, rapporto paura/suo massimo a 63 sedute, paura a 1 mese/paura a 3 mesi (dal 2007), variazione a 21 sedute e rapporto con il massimo a 63 sedute dello spread del credito (Baa), quota di settori sopra la media a 50 sedute.

## Bersagli
- **F1** nelle 21 sedute successive l'S&P 500 scende ancora di almeno il 5% sotto la chiusura di oggi (= «continua a calare»).
- **F3** il rendimento delle 21 sedute successive è positivo e nelle 21 sedute non è mai sceso più del 2% (= «minimo toccato, cresce»).
- **R** rendimento delle 21 sedute successive (misura continua).

## Modelli (6, configurazioni fisse)
- **G0** Minimi attuale (min fra panico recente e 100 − svolta), riferimento.
- **G1** regressione logistica (regolarizzazione forte, C=0,1, variabili standardizzate), solo variabili P, bersaglio F1, addestrata su tutti i giorni.
- **G2** come G1 con P+V.
- **G3** come G1 ma addestrata solo sui giorni «sotto stress» (S&P 500 ≥ 8% sotto il massimo a 252).
- **G4** come G3 con P+V.
- **G5** alberi potenziati (profondità 2, 100 alberi, passo 0,05), P+V, tutti i giorni.
Il valore da 1 a 100 è il percentile della probabilità prevista nella storia di previsioni passate (percentile espanso, solo passato).

## Misura
Perimetri: tutti i giorni e giorni sotto stress. Per F1: AUC. Per F3: AUC del punteggio invertito. Per R: correlazione di Spearman (attesa negativa). Intervallo al 90%: bootstrap per anno (500). Soglia del caso: 95° percentile del migliore tra i 6 modelli con bersagli mescolati per anno (200 prove). Verifica principale: previsioni dal 2013; secondaria: 1975-2012 (G1, G3) e 1999-2012 (G2, G4, G5), tutte fuori campione. Anche: rendimento medio a 21 sedute nei giorni sotto stress con punteggio ≥ 80 e ≤ 20.

## Criterio di adozione come nuovo Minimi
Il modello migliore tra G1–G5 sostituisce la formula attuale solo se, nei giorni sotto stress, in verifica dal 2013: (a) AUC su F1 sopra la soglia del caso con limite inferiore IC90 > 0,5; (b) AUC su F3 sopra 0,5 con limite inferiore IC90 > 0,5; (c) rendimento medio a 21 sedute con punteggio ≥ 80 minore di quello con punteggio ≤ 20; (d) supera G0 su F1 e F3. Se nessuno passa, il Minimi resta com'è con l'avviso «non dimostrato» e l'esito dice perché.
