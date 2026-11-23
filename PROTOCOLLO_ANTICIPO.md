# Protocollo: l'Indice crollo deve avvisare PRIMA (anticipo di almeno un giorno)

Scritto e pubblicato prima di calcolare i risultati (23 novembre 2026). Nessuna regola cambia dopo.

## Il problema (richiesta dell'utente)
L'Indice crollo si accorge del crollo mentre avviene. Il giorno prima, nelle crisi di origine finanziaria, è spesso basso. Deve invece segnalare che il mercato è predisposto al crollo, ai valori da 1 a 100, con anticipo di almeno 24 ore.

## Diagnosi (descrittiva, prima delle prove)
1. Quanto è reattivo l'indice di oggi: correlazione tra l'indice al giorno t e il rendimento dei 5 giorni PRECEDENTI contro la correlazione con il calo massimo dei 5 giorni SUCCESSIVI.
2. Composizione: peso delle famiglie «reattive» (paura f1, salto paura f2, curva paura f3, prezzo sotto le medie f7, distanza dal massimo f8, ballo dei prezzi f9) contro quelle di «predisposizione» (protezioni f4, credito f5, tassi f6, fuga dai settori f10, titoli di Stato f11, Indice Armor f12).
3. Per ogni crisi finanziaria della lista CLASSIFICA dal 1991 (esterne e miste escluse): percentile dell'indice il giorno prima del primo −3% in 5 sedute da vicino ai massimi.

## Bersaglio principale: «crollo a freddo»
Giorni t (fuori dalle finestre di shock esterno e dalle due crisi miste) in cui l'S&P 500 è entro il 3% dal massimo a 252 sedute. Evento = il minimo dei prossimi 5 giorni di Borsa è almeno −4% rispetto alla chiusura di t (bersaglio B5) oppure il minimo dei prossimi 10 è almeno −6% (B10). Si valuta l'indice al giorno t, quindi con anticipo di un giorno o più rispetto alla caduta.
Periodi: scelta fino al 2014, verifica dal 2015. Se gli episodi indipendenti (separati da 20 sedute) sono meno di 12 nel totale, l'esito è dichiarato «non valutabile con certezza» e i risultati restano descrittivi.
Bersagli di controllo (già usati): −3% a 5 sedute, −5% a 21, −8% a 63, su tutti i giorni del perimetro.

## Candidati (fissati ora)
- BASE: Indice crollo attuale (colonna indice).
- R: media dei percentili delle famiglie reattive f1, f2, f3, f7, f8, f9.
- P (predisposizione): media dei percentili di CAPE, Indice Buffett (ritardo 90 giorni), debito a margine annuo (ritardo 50), credito f5, protezioni f4, scosse sui tassi f6, fuga dai settori f10, titoli di Stato f11, condizioni finanziarie nfci, prosciugamento della liquidità (−net_liq_13w).
- M5: massimo dell'indice BASE negli ultimi 5 giorni di Borsa (non fa scendere l'indice il giorno prima).
- E3: media mobile esponenziale a 3 giorni dell'indice BASE.
- B1: 0,5·rank(BASE) + 0,5·rank(P).
- B2: M5 applicato a B1.
Percentile espanso (solo passato). Misura: AUC sul bersaglio principale.

## Regola di adozione (per sostituire o integrare BASE)
Un candidato diventa il nuovo Indice crollo se, rispetto a BASE, l'AUC sul bersaglio B5 e sul B10 sale di almeno +0,03 sia in scelta sia in verifica, e nei tre bersagli di controllo non peggiora di più di −0,01 in nessun periodo. Se più candidati passano, si prende quello con meno componenti reattive. Esito: «Coerente con i casi osservati» / «Non coerente». Mai «provato».

## Se nulla passa
Si dice chiaramente che con i dati a disposizione l'anticipo di un giorno non è dimostrabile; resta il termometro. Si aggiunge comunque, come informazione separata, la «predisposizione» P con i fattori che la spingono (non cambia il numero dell'Indice crollo) e si registra ogni giorno per la prova in avanti.

## Emendamento 1 (23 novembre 2026, 12:45, prima dei nuovi calcoli): l'ipotesi «troppo peso alla paura»
Ipotesi dell'utente: se l'indice si basa sulla paura (VIX), si alza solo quando il crollo è già iniziato; deve anticipare l'aumento della paura.
Nuovi candidati (stessi dati, nessuna soglia cambiata):
- NP: Indice crollo ricalcolato SENZA le tre famiglie di paura (f1 paura, f2 salto della paura, f3 curva della paura): stessi pesi delle altre, rinormalizzati, stessa scala a percentili.
- RP: solo famiglie di prezzo (f7 tendenza, f8 perdita, f9 ballo dei prezzi), media dei percentili.
- NP2: come NP ma senza anche f7 e f8 (il prezzo già sceso): resta solo credito f5, tassi f6, rotazione f10, protezioni f4, titoli di Stato f11, Indice Armor f12.
- C1: 0,5·rank(NP) + 0,5·rank(P).
- C2: 0,5·rank(NP2) + 0,5·rank(P).
Nuovo bersaglio «paura in arrivo»: giorni con VIX sotto 22 in cui il massimo del VIX nelle prossime 5 sedute è almeno +35% rispetto a oggi. Si misura l'AUC di ogni candidato (scelta fino al 2014, verifica dal 2015; stessi perimetri). Serve a dire se un indice senza paura anticipa l'aumento della paura.
Regola di adozione: identica a quella già scritta (+0,03 su B5 e B10 in entrambi i periodi, senza peggiorare i controlli di più di −0,01), con in più AUC sul bersaglio «paura in arrivo» non peggiore di −0,02 in entrambi i periodi rispetto a BASE. Se NP, NP2, C1 o C2 la passano, sostituiscono l'Indice crollo. Esito: «Coerente con i casi osservati» / «Non coerente».
