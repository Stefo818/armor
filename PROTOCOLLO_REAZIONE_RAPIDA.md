# Protocollo: un indice Crollo che reagisce in pochi giorni (26/11/2026)

Pubblicato PRIMA di calcolare. Richiesta dell'utente: accorgersi di un crollo «qualche giorno prima», non mesi; l'indice prima del crollo deve essere piu' alto.

## Fatto di partenza (misurato oggi sull'indice attuale, 12 picchi endogeni)
Media dell'indice nelle ultime 3/5/10/20 sedute fino al picco: 23,5 / 24,2 / 25,8 / 28,8, contro 22,5 nei giorni calmi. A pochi giorni dal picco l'indice non e' quasi sopra il livello dei mercati calmi: in 5 crolli su 12 e' sotto 10. Cioe' i massimi non si preannunciano; e' un limite gia' visto (ESITO_ANTICIPO_CROLLI, ESITO_RICERCA_200000: 0 picchi su 97 coperti dopo mercati calmi).

## Cosa si prova (nuova domanda realistica)
Non «prevedere il picco» ma **accorgersi in fretta dell'inizio del crollo**: dopo quanti giorni dal picco suona l'allarme, e quanta parte della discesa e' ancora davanti.
Per ogni picco p: allarme = primo giorno t in [p-10, p+40 sedute] con indice >= soglia. Misure:
- ritardo = t - p (sedute; negativo = prima del picco; nessun allarme = 40);
- discesa residua = (prezzo(t) - minimo(p..p+60)) / (prezzo(p) - minimo(p..p+60)), tra 0 e 1: quota di discesa ancora da fare quando suona l'allarme (nessun allarme = 0).
Soglia di ogni candidato fissata solo sui giorni calmi fino al 2007: il valore superato dal 5% di quei giorni. Cosi' tutti hanno lo stesso numero di falsi allarmi.

## Candidati (fissati ora)
0. Indice attuale.
1. Veloce: 30% salto del VIX (5 e 10 giorni), 25% VIX sopra VIX a 3 mesi, 20% livello del VIX, 25% volatilita' dei soli ribassi a 5 giorni; tutti in percentile.
2. Veloce con dati nuovi: come 1, ma VIX sopra VIX3M al 10%, VIX9D sopra VIX 15% e VVIX 15% (percentili; 50 prima del 2011 per le serie nuove).
3. Massimo fra indice attuale e veloce (1), ognuno in percentile.

## Regola di accettazione (tutte insieme, sulla VERIFICA = 5 picchi dal 2018)
(a) discesa residua media (cioe. quota ancora da subire) inferiore di almeno 0,10 a quella dell.indice attuale; (b) falsi allarmi nei giorni calmi dal 2008 non oltre +1 punto percentuale rispetto all'attuale; (c) in selezione (7 picchi fino al 2011) non peggiore dell'attuale. Con soli 5 picchi anche un passaggio resta «da confermare in avanti».

## Anche in caso negativo
Esito scritto in ESITO_REAZIONE_RAPIDA.md. Nessun candidato nuovo dopo aver visto i numeri.
