# Protocollo: il Super Armor anticipa l'economia dei prossimi mesi? (25 novembre 2026)

Scritto PRIMA di calcolare. Nessuna regola cambia dopo; l'esito si pubblica anche se negativo.

## Domanda dell'utente
Il Super Armor dovrebbe dire come sarà l'economia fra qualche mese, incrociando dati finanziari (veloci, anticipano) ed economici (lenti, descrivono l'economia già in corso) con i pesi giusti. Lo fa il Super Armor di oggi? Qual è la formula migliore? Almeno 20 alternative.

## Bersagli (fissati ora)
- **Z6 «economia fra 6 mesi»** (misura continua, principale): media di tre cambiamenti dal mese t al mese t+6, ciascuno in scala standard (dev. standard dell'intero campione, solo per la scala): meno la variazione della disoccupazione, crescita dei posti di lavoro, crescita della produzione industriale. Alto Z6 = economia che migliora. Il punteggio da valutare è «economia in peggioramento» = −Z6. Dati finali (rivisti) come bersaglio; i punteggi usano solo i valori noti alla data, con i ritardi di pubblicazione reali (disoccupazione/Sahm 40 giorni, produzione 45, posti di lavoro 37, indice di Chicago 45, vendite 45, fiducia 20, permessi 45, sussidi 5, mercati 1).
- **R6 «recessione entro 6 mesi»** (secondario): nei mesi in cui non c'è recessione, 1 se la datazione ufficiale NBER mostra l'inizio di una recessione nei 6 mesi successivi.
Un punto al mese (ultimo giorno del mese).

## Componenti (percentili storici solo del passato, espansi dal 1976; alto = peggio)
Finanziarie: F1 curva dei tassi (10 anni − 3 mesi, invertita); F2 spread del credito (Baa−10 anni) livello; F3 spread del credito, variazione a 6 mesi; F4 condizioni finanziarie (NFCI); F5 S&P 500: rendimento a 12 mesi (invertito); F6 curva 10 anni − 2 anni (invertita); F7 paura (VIX, dal 1990).
Economiche: E1 richieste di sussidio (media 4 settimane rispetto al minimo a 52 settimane); E2 posti di lavoro, crescita a 3 mesi (invertita); E3 produzione industriale, crescita a 3 mesi (invertita); E4 indice di Chicago (invertito); E5 permessi di costruzione, variazione a 6 mesi (invertita); E6 indicatore di Sahm; E7 fiducia dei consumatori, variazione a 6 mesi (invertita).

## 26 alternative (formule e pesi fissati ora)
Singole: C1 F1 · C2 F2 · C3 F4 · C4 F5 · C5 E1 · C6 E4 · C7 E2 · C8 E5 · C9 E6.
Medie: C10 media uguale delle finanziarie F1–F6 · C11 media uguale delle economiche E1–E7 · C12 50% finanziarie + 50% economiche · C13 70% fin + 30% eco · C14 30% fin + 70% eco · C15 media uguale di tutte le 14 · C16 il peggiore fra fin e eco (massimo) · C17 prodotto (fin × eco / 100) · C18 pesi uguali sulle tre componenti migliori nel periodo di scelta (1976–2004) · C19 curva + credito + sussidi + posti di lavoro (quattro «classici», uguali) · C20 pesi proporzionali all'anticipo (finanziarie peso 3, economiche peso 1) · C21 finanziarie veloci F1,F3,F4,F5 + economiche anticipatrici E1,E5,E7 (uguali) · C22 «la finanza guida, l'economia conferma»: fin × (50 + eco/2)/100.
Addestrate a scorrimento (solo dati passati, ogni anno riaddestrate): C23 regressione logistica regolarizzata (C=0,1) su tutte le componenti, bersaglio R6 · C24 regressione ridge (alfa=10) su tutte le componenti, bersaglio −Z6 · C25 prima componente principale (espansa) delle 14.
Riferimenti attuali di Armor: **C26 Super Armor di oggi** (titan_storia.csv, dal 1990) e, per confronto, l'Indice Armor (armor_tarato).

## Periodi
Scelta 1976–2004; verifica 2005–2026 (comprende 2008 e 2020). Confronto con il Super Armor di oggi: solo dal 1990 (suo inizio). Le addestrate producono previsioni dal 1986.

## Misure
Per ogni alternativa: correlazione di Spearman fra il punteggio e −Z6 (alto = peggioramento: atteso positivo), AUC su R6; intervallo al 90% con bootstrap per anno (500); soglia del caso = 95° percentile del migliore Spearman (o AUC) fra le alternative con bersagli mescolati per anno (200 prove). Anticipo: correlazione con −Z6 anche con il punteggio spostato di 3 e di 9 mesi avanti.

## Criterio di adozione
Una formula sostituisce quella dell'«economia fra qualche mese» solo se, in verifica 2005–2026: (a) il suo Spearman con −Z6 supera la soglia del caso con limite inferiore IC90 > 0; (b) supera il Super Armor di oggi di almeno 0,05 sullo stesso periodo; (c) è fra le prime 3 anche in scelta (non solo in verifica); (d) AUC su R6 > 0,5 con limite inferiore IC90 > 0,5. La scelta fra le tre migliori è fatta in scelta, non in verifica. Se nessuna passa, la domanda dell'utente ottiene risposta negativa e si mostra la migliore come indizio, con peso zero.
