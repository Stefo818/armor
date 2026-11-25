# Protocollo: indice di fase «verso il minimo / lontano dal minimo» (25 novembre 2026)

Scritto PRIMA di calcolare. Sostituisce il Protocollo 4 (mai concluso: il calcolo si era interrotto, nessun risultato visto). Del Protocollo 3 si conosce l'esito negativo (ESITO_MINIMI_2 e dati preliminari): i bersagli «scende ancora del 5%» e «sale» non erano misurabili con pochi episodi.

## Richiesta dell'utente
Considerare solo episodi di crisi finanziaria / interna al mercato (niente cigni neri). Un indice che dica se il mercato sta **avvicinandosi a un minimo** (valore alto, rosso: la discesa è in corso e il fondo è ancora davanti) o **allontanandosi dai minimi verso nuovi massimi** (valore basso, verde). Provare anche idee nuove, ispirate alla letteratura.

## Fonti consultate (idee da cui nascono i punteggi)
Datazione dei cicli toro/orso (Bry-Boschan, Pagan-Sossounov), cambi di regime (Hamilton; Maheu-McCurdy), dipendenza dalla durata (le discese lunghe hanno più probabilità di finire), picco di paura e minimo di prezzo (il picco del VIX coincide spesso col minimo), spinta di ampiezza (Zweig: molti titoli/settori che risalgono insieme), credito che smette di peggiorare (Kindleberger, Minsky), asimmetria della volatilità (la volatilità cala prima dei prezzi che risalgono), rimbalzo dai minimi come conferma tardiva.

## Bersaglio (nuovo, diretto)
Per ogni mercato, una **discesa** è un periodo continuo con prezzo ≥ 8% sotto il massimo a 252 sedute (due periodi separati da meno di 21 sedute sono uno solo). In ogni discesa il **minimo** è la seduta con il prezzo più basso. Un giorno della discesa è **«fondo davanti»** (T=1) se è prima del minimo, **«fondo alle spalle»** (T=0) se è dopo. Sono esclusi i giorni in finestre di shock esterni (stesse liste ESTERNI e MISTE_MAX di classifica_40anni, finestre usate nei protocolli precedenti). Il giorno del minimo stesso è escluso.

## Punteggi (fissati ora; alto = fondo davanti)
- **B0** 100 − «Segni di svolta» dell'Minimi attuale (solo S&P 500, riferimento di Armor).
- **N1** −(sedute dal massimo a 252): le discese lunghe sono più avanti (riferimento ingenuo di durata).
- **N2** −(rimbalzo dal minimo a 63 sedute) (riferimento ingenuo di prezzo).
- **L1** regressione logistica (C=0,1) sulle 13 variabili di prezzo del Protocollo 3 (aggiungendo: sedute dal massimo a 252, picco della volatilità a 21 sedute nelle ultime 63 e rapporto volatilità/suo picco), addestrata sui giorni in discesa di tutti i mercati con scorrimento annuale.
- **L2** come L1 aggiungendo (solo dove esistono, dal 1999 sull'S&P 500) paura in percentile, paura/suo massimo a 63, spread del credito/suo massimo a 63 e quota settori sopra la media a 50 sedute (modello S&P 500 solo).
- **L3** media semplice di percentili espansi (nessun addestramento): volatilità/suo picco, rimbalzo dal minimo (con segno invertito), sedute dal massimo (invertito), pendenza media a 50 (invertita), giorni neri a 21 sedute.
- **E1** media dei punteggi percentili L1 e L3.
Percentili calcolati solo sul passato dello stesso mercato. Il valore da 1 a 100 è il punteggio percentile.

## Mercati (dati già salvati)
S&P 500, FTSE, CAC, SMI, IBEX, AEX, BEL 20, Hang Seng, Toronto, Sydney, San Paolo, Seul, Taiwan, Messico (storia dal 1990 circa; un solo indice USA).

## Misura
AUC (alto = fondo davanti) sui giorni delle discese di tutti i mercati, previsioni fuori campione dal 2000 (scorrimento annuale con 95 giorni di salto). Intervallo al 90%: bootstrap per discesa (500). Soglia del caso: 95° percentile del migliore AUC fra i punteggi quando il bersaglio è spostato in modo circolare a caso dentro ogni discesa (200 prove). Per mercato: AUC e quante discese su quante hanno AUC > 0,5. Solo S&P 500: AUC di B0, L2, L3 (dove disponibili).

## Criterio di adozione
Un punteggio entra nell'app come nuovo Minimi solo se: (a) AUC sopra la soglia del caso e limite inferiore IC90 > 0,5; (b) supera N1 e N2 di almeno 0,03 AUC (deve aggiungere qualcosa oltre «durata» e «prezzo»); (c) almeno il 65% delle discese ha AUC > 0,5; (d) vale anche sul solo S&P 500 con AUC > 0,5. Altrimenti il Minimi resta com'è con l'avviso «non dimostrato».
