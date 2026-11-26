# Protocollo giro 2: Indice Crollo che si alza prima dei picchi (26/11/2026)

Pubblicato PRIMA di calcolare. Segue ESITO_CROLLO_V3.md (giro 1 negativo). Idea: insegnare al modello il bersaglio che interessa all'utente, cioe' «il massimo del mercato arrivera' nei prossimi 10 giorni e dopo ci sara' un calo di almeno l'8%», e tenere la capacita' di separare i giorni rischiosi mescolando con il vecchio indice.

## Bersaglio Yp «picco in arrivo»
Un giorno s e' un picco se la sua chiusura e' la massima fra s-60 e s+40 sedute e il minimo delle 40 sedute dopo e' almeno l'8% piu' basso. Yp(t) = 1 se un picco cade fra t e t+9 (oggi compreso). Tutti i picchi dal 1990 (anche da shock esterni) per l'addestramento; la valutazione dei picchi usa i 5 crolli endogeni 2018-2024.
Per la separazione dei giorni rischiosi si usa ancora Yb (calo profondo a 60 sedute, come nell'app).

## Candidati (otto, fissati ora)
Stesso addestramento, stesse finestre e stesse protezioni del giro 1 (finestra crescente da 2001, 70 sedute di scarto, logistica C=0,5, alberi profondita' 3).
P1 L-F1-p · P2 G-F1-p · P3 L-F2-p · P4 G-F2-p (solo bersaglio Yp, con F1 e F2 del giro 1).
Q1..Q4: stessa cosa ma il punteggio finale e' la media dei percentili di Pk e del vecchio indice (cosi' si tiene la capacita' di separare).
Scelta in 2001-2014 con la media fra AUC su Yp e AUC su Yb; verifica dal 2015. Soglia del caso: massimo dell'AUC su Yp (2015+) fra gli otto candidati con etichette spostate in circolo (300), 95° percentile.

## Regola di accettazione (tutte insieme, sul vincitore nel 2015+, rispetto al vecchio)
(i) AUC su Yp almeno +0,05 sul vecchio e sopra la soglia del caso; (ii) tabella per zona: giallo o peggio contro verde almeno 2 (tutti), 1,5 (fra -2% e -7%), 1,3 (vicino ai massimi); (iii) stacco 10 sedute prima dei 5 picchi meno giorni calmi: +5 punti sul vecchio; (iv) falsi allarmi non oltre +1 punto percentuale sul vecchio; (v) protezione almeno +0,10 sul vecchio.
Esito in ESITO_CROLLO_V3B.md anche se negativo.
