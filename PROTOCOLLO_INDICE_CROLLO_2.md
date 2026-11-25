# Protocollo: «Indice crollo 2», dieci proposte per anticipare i crolli di origine finanziaria

Scritto e pubblicato PRIMA di calcolare qualsiasi risultato (25 novembre 2026). Nessuna regola cambia dopo.

## Perché
L'utente osserva che l'Indice crollo attuale è troppo legato al presente: la paura (VIX) e la distanza dal massimo si accendono quando il calo è già in corso. Chiede: (a) provare 4 sue ipotesi; (b) aggiungere 6 proposte nuove, fondate sulla letteratura economica; (c) misurare tutto e vedere quale dà il segnale migliore di anticipo dei crolli endogeni.

## Bersagli e giorni valutati (identici a PROTOCOLLO_SFASATO.md, non cambiano)
Solo giorni di «partenza da fermo»: S&P 500 entro il 5% dal massimo a 252 sedute e non sceso più del 2% nelle ultime 5 sedute. Perimetro finanziario: tolti da 63 sedute prima a 60 dopo ogni shock esterno (lista ESTERNI) e da 5 prima a 180 dopo le due crisi miste.
- E1 (giorni): minimo a t+1…t+5 ≤ −3%.
- E2 (settimane): minimo a t+6…t+21 ≤ −5% e senza −3% nei 5 giorni prima.
- E3 (mesi): minimo a t+22…t+63 ≤ −8% e senza −5% nelle 21 sedute prima.
Scelta: fino al 2014. Verifica: dal 2015, mai usata per scegliere. Ogni punteggio è usato con segno fissato qui sotto (più alto = più rischio), non scelto dopo.

## Le 4 proposte dell'utente (varianti dell'indice)
Punteggio base S = media pesata delle famiglie come ora (pesi M2: paura 0,30, curva della paura 0,30, credito 0,15, tendenza 0,25, perdita dal massimo 0,25, rotazione 0,15, tassi 0,15), trasformata in percentile espanso (solo passato).
- **V1** indice attuale (riferimento).
- **V2** senza «distanza dal massimo» (f8): stessi pesi delle altre, normalizzati.
- **V3** V1 con il candidato D07 (CAPE × prezzo sotto la media a 200 giorni, come in spia_caro.py): 0,8·percentile(S) + 0,2·percentile(D07).
- **V4** V2 con D07 (stessa miscela 0,8 / 0,2).

## Le 6 proposte nuove (letteratura; punteggio autonomo e anche misto con V1)
Tutte come percentile espanso (minimo 252 osservazioni giornaliere o 60 mensili); ritardi di pubblicazione: mensili 45 giorni, settimanali 7, giornalieri 1. Prodotto = prodotto dei percentili (alto solo se entrambi alti).
- **N1 «Boom di credito e di prezzi insieme»** (Greenwood, Hanson, Shleifer, Sørensen: le crisi sono prevedibili quando credito e prezzi salgono insieme): percentile della crescita a 3 anni dei prestiti alle imprese (busloans) × percentile del rendimento a 3 anni (756 sedute) dell'S&P 500.
- **N2 «Credito che si rovina dal basso»** (Lopez-Salido, Stein, Zakrajšek: spread bassi = fiducia eccessiva, poi si allargano): (1 − percentile del livello dello spread Baa−10 anni) × percentile della sua variazione a 20 sedute.
- **N3 «Calma che prepara la tempesta»** (Minsky: la stabilità genera instabilità; Baron-Xiong: espansione quando i prezzi sono alti): (1 − percentile della volatilità realizzata a 63 sedute) × percentile del CAPE.
- **N4 «Salita eccessiva con volatilità»** (Greenwood, Shleifer, You, «Bubbles for Fama»: una forte salita prevede probabilità di crollo più alta, soprattutto con alta volatilità): percentile del rendimento a 504 sedute × percentile della volatilità realizzata a 63 sedute.
- **N5 «Terreno fragile × innesco»** (Kindleberger-Minsky: serve terreno fragile più un innesco): percentile della predisposizione P (media dei dieci componenti come in predisposizione.py, almeno 5 disponibili) × percentile della media di «salto della paura» (f2) e «paura a breve contro tre mesi» (f3).
- **N6 «Stretta di liquidità e tassi»**: media (disponibili, almeno 2) dei percentili di: liquidità netta che si prosciuga (−variazione a 13 settimane, dal 2003), variazione a 13 settimane delle condizioni finanziarie (NFCI), salita del rendimento a 2 anni in 63 sedute.
Ogni nuova proposta è valutata (a) da sola e (b) in miscela 0,5·percentile(V1) + 0,5·percentile(Ni). Totale punteggi misurati: 4 + 6 + 6 = 16. Dove un punteggio manca (serie troppo corta) vale 0,5, quindi non favorisce.
Pesi: nessuna ottimizzazione dei pesi sui dati; tutti fissati qui (miscele 0,8/0,2 e 0,5/0,5 e prodotti), perché con pochi episodi un peso «imparato» si adatta al rumore.

## Misure
Per ogni punteggio e ogni evento: AUC in scelta e in verifica, intervallo al 90% (bootstrap per anno, 1.000 ripetizioni), episodi indipendenti (eventi separati da più di 20 sedute) per periodo. Soglia del caso: 95° percentile del migliore AUC di verifica tra tutti i 16 punteggi con bersagli mescolati per blocchi d'anno (200 prove, seme fisso). Se gli episodi in verifica sono meno di 6, l'evento non è valutabile (probabile E3).

## Regole di accettazione
Un punteggio X sostituisce l'Indice crollo attuale (V1) solo se:
- **A1** su E1: AUC(X) ≥ AUC(V1) + 0,03 sia in scelta sia in verifica;
- **A2** su E2: AUC(X) non peggiora di più di 0,02 rispetto a V1 in nessuno dei due periodi;
- **A3** su E1: AUC verifica di X sopra la soglia del caso (migliore di 16);
- **A4** limite inferiore dell'intervallo al 90% in verifica sopra 0,55.
Se più punteggi passano, si prende quello con AUC di scelta più alta su E1 (mai guardando la verifica). Se nessuno passa, resta V1 e si dichiara che nessuna delle 16 versioni anticipa meglio. Esito: «Coerente con i casi osservati» / «Non coerente»; mai «provato». L'esito si scrive comunque. Se un punteggio passa solo A1 ma non A3, è un indizio: resta fuori dall'indice e va in registro per la prova in avanti.

## Cosa NON si fa
Nessuna soglia, peso, orizzonte o formula cambia dopo aver visto i numeri. Nessun candidato è aggiunto dopo i calcoli (altre idee vanno in un protocollo successivo).
