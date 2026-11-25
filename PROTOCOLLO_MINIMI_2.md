# Protocollo: Minimi riletto «continua a scendere» (25 novembre 2026)

Scritto PRIMA di calcolare. Nessuna regola cambia dopo; l'esito si pubblica anche se negativo.

## Richiesta dell'utente
Minimi a 1 = il mercato ha smesso di scendere (minimo già toccato, rialzo medio nelle prossime settimane). Minimi a 100 = il mercato continua a scendere e non si vede la fine (ancora molto ribasso nelle prossime settimane). L'indice attuale (alto = minimo probabile) dice il contrario nei momenti di panico: va misurato se la lettura nuova regge.

## Punteggi (4, fissati ora; stesse voci di occasione.py, nessun peso ottimizzato)
- **M0** 100 − Minimi attuale (solo inversione; in mercato calmo darebbe un valore alto, quindi è il riferimento «sbagliato»).
- **M1** minimo fra Panico recente (massimo a 63 sedute) e (100 − Svolta): alto solo se c'è stato panico E non ci sono segni di svolta; basso se non c'è panico o se la svolta c'è.
- **M2** M1 solo quando l'S&P 500 è almeno 8% sotto il massimo a 252 sedute, altrimenti 1.
- **M3** Indice crollo (riferimento esistente).

## Bersagli
- **F1** nelle 21 sedute successive l'S&P 500 scende ancora di almeno il 5% sotto la chiusura di oggi.
- **F2** nelle 63 sedute successive scende ancora di almeno l'8%.
Due perimetri: **tutti i giorni** e **giorni sotto stress** (S&P 500 almeno −8% dal massimo a 252 sedute). Shock esterni non esclusi (per un minimo conta il prezzo, non la causa).

## Misura
AUC (alto = più discesa dopo). Scelta: fino al 2012. Verifica: dal 2013. Intervallo al 90%: bootstrap per anno (500). Soglia del caso: 95° percentile del migliore AUC di verifica fra i 4 punteggi con bersagli mescolati per anno (200 prove). In più: rendimento medio delle 21 sedute successive nei giorni con M1 ≥ 80 contro M1 ≤ 20 (verifica, solo giorni sotto stress).

## Criterio
La lettura nuova si può **dichiarare nell'app come «misurata»** solo se M1 o M2, nei giorni sotto stress, in verifica supera la soglia del caso su F1 o F2 e ha limite inferiore dell'IC90 sopra 0,5. Altrimenti si mostra comunque la lettura nuova (scelta di prodotto dell'utente) con la dicitura esplicita «non dimostrato: indizio».
