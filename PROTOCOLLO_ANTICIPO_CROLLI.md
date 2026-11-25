# Protocollo: cosa si rompe prima di un crollo improvviso? (≥ 8% in 5 sedute) — 25/11/2026 sera

Scritto prima di calcolare un solo risultato. Nessuna regola cambia dopo aver visto i numeri.

## Domande dell'utente
1. Quanti giorni prima l'Indice Crollo inizia ad alzarsi prima di un crollo (perdita ≥ 8% in 5 sedute)?
2. Se non anticipa, cosa anticipa? Provare un centinaio di ipotesi (compresa quella dell'utente: il mercato prova a salire, si ferma più volte sotto lo stesso livello, poi la sfiducia sale) e cercare segnali che arrivino almeno 2 sedute prima, meglio 5.

## Crollo e giorno zero
Serie S&P 500 chiusure giornaliere. Per ogni seduta d: f5(d) = minimo delle chiusure d+1…d+5 diviso la chiusura di d, meno 1. Giorno zero (t0) = prima seduta con f5 ≤ −8%; un nuovo episodio parte solo dopo 60 sedute dall'ultimo giorno con f5 ≤ −8%. Periodo 1990-01-01 → oggi (dati di opzioni dal 1990). Episodi: 13 (1997-10-20, 1998-08-24, 2000-04-07, 2001-09-04, 2002-07-15, 2008-09-22, 2011-08-01, 2015-08-17, 2018-02-01, 2020-02-20, 2022-05-04, 2025-03-28, 2026-11-13). Qui sono inclusi anche i crolli esterni (11 settembre, Covid): la domanda riguarda i crolli improvvisi in generale; si riporta anche il risultato senza 2001 e 2020.
Finestra di avviso W = sedute t0−10 … t0−2 (il segnale deve esistere alla chiusura di t0−2 o prima: almeno 2 sedute di anticipo). Sotto-finestre: W2 = t0−3…t0−2, W5 = t0−6…t0−4, W10 = t0−10…t0−7.
Giorni di confronto (base): tutte le sedute dal 1992 che non cadono in [t0−60, t0+5] di nessun episodio.

## Parte 1 — Indice Crollo e Armor
Per ogni episodio, sulla serie giornaliera dell'indice: (a) sedute prima di t0 in cui l'indice supera per la prima volta 50 e 60 (entro 60 sedute; altrimenti «mai»); (b) sedute dall'ultimo minimo locale nelle 40 sedute prima (inizio della salita); (c) valore a t0−2, t0−5, t0−10 e confronto con la media dei giorni di base. Descrittiva, nessuna selezione. Stesse misure di capacità (AUC come sotto) per Crollo, Armor, Minimi come riferimento.

## Parte 2 — Ipotesi (N ≈ 100, esatto dichiarato dallo script; direzione scelta ora)
Ogni ipotesi è una misura calcolata con i dati noti alla chiusura del giorno; direzione fissata: «+» = valore alto è rischio, «−» = valore basso è rischio. Dove la direzione è davvero ambigua si provano entrambe come ipotesi separate. Le misure sono trasformate in percentile «espanso» (solo passato, minimo 500 giorni).
- **Struttura dei prezzi (S&P, chiusura/massimo/minimo/volume):** giorni vicini al massimo (entro 1%, 0,5% del massimo a 252 e a 60 sedute) nelle ultime 10/20 sedute (+); rotture fallite (massimo sopra il massimo a 60 giorni ma chiusura sotto) in 20 sedute (+); sedute dal massimo a 252 (+); distanza dal massimo a 252 (−, cioè vicino ai massimi); ampiezza media (massimo−minimo) 5/60 (+) e 20/60 (−); volatilità realizzata 5, 10, 20 giorni (+ e −), rapporto 10/60 (+); volatilità in discesa / in salita 20 (+); quota di giorni in rialzo in 20 (+ e −); rendimento a 3, 5, 10, 20, 60 sedute (+ e −); distanza dalla media a 50 e 200 giorni (+); pendenza della media a 50 su 10 giorni (−); peggior giornata e giorni sotto −1% in 5/10 sedute (+); gap al ribasso (apertura sotto la chiusura precedente di 0,3%) in 10 (+); posizione della chiusura nel range del giorno, media 5 (−); ombra superiore media 10 (+); volume 5/60 (+ e −); volume dei giorni in calo / in rialzo 20 (+); asimmetria 20 (−), curtosi 60 (+); autocorrelazione a 1 giorno su 20 (+ e −); nuovi minimi a 20 giorni in 10 sedute (+); massimo a 10 giorni diviso massimo dei 20 precedenti (−); rendimento 60 / volatilità 60 (+).
- **Paura e opzioni:** livello del VIX (+ e −), variazione a 5 giorni (+), VIX/media a 60 (+), VIX/volatilità realizzata 20 (+ e −), correlazione a 20 giorni fra variazioni del VIX e rendimenti dell'S&P (+, cioè VIX che sale con la Borsa), giorni con VIX in salita e S&P in salita in 10 (+), indice dell'asimmetria delle opzioni (SKEW) livello (+) e variazione 10 giorni (+), massimo del VIX a 10 giorni / media 60 (+), prodotto fra «S&P entro 2% dal massimo» e variazione VIX a 5 giorni (+).
- **Credito e tassi:** differenziale Baa-10 anni (livello, var. 5 e 20 giorni, +), spread alto rendimento e investment grade (var. 5 e 20, +), indice di stress CISS Usa (livello e var. 5, +), curva 10 anni-3 mesi (livello e var. 20, −), variazione assoluta del rendimento a 10 anni in 5 giorni (+), variazione 20 giorni a 10 e 2 anni (+), dollaro (var. 5 e 20, +), cambio col yen (variazione assoluta a 5 giorni, +).
- **Altri mercati:** Nasdaq 100/S&P (var. 20, + e −), piccole aziende/S&P (var. 20, + e −), medie aziende/S&P (−), S&P 100/S&P (+), Europa (DAX) e Giappone (Nikkei) meno S&P a 5 giorni (−), DAX e Nikkei a 20 giorni (−); dal 1999: settori difensivi/ciclici (var. 20, +), finanza/S&P (var. 20, −), tecnologia/S&P (+ e −), consumi voluttuari/beni di base (−), servizi pubblici/S&P (+), quota di 9 settori sotto la loro media a 50 (+), dispersione dei rendimenti a 5 giorni fra settori (+), correlazione media a 20 giorni fra settori (+), numero di settori ai massimi a 60 giorni (−).
- **Calendario:** agosto-ottobre (+), settimana della scadenza trimestrale delle opzioni (+).
Riferimenti non contati in N: Indice Crollo, Armor, Minimi.

## Misura e convalida
Misura primaria di ogni ipotesi: AUC pesata per episodio: per ogni episodio la probabilità che un giorno di W abbia percentile più «a rischio» di un giorno di base; media degli episodi (ogni episodio pesa uno; episodi senza dati della misura esclusi).
Divisione nel tempo: **selezione** = episodi fino al 2011 (7: 1997, 1998, 2000, 2001, 2002, 2008, 2011); **verifica** = dal 2015 (6: 2015, 2018, 2020, 2022, 2025, 2026). Si sceglie solo sulla selezione.
Soglia contro il caso («migliore fra N»): 300 spostamenti circolari casuali dei 13 giorni zero (almeno 250 sedute); per ognuno si ricalcola l'AUC di selezione di tutte le ipotesi e si prende il massimo. L'ipotesi passa la selezione se: AUC selezione ≥ 0,65 **e** maggiore del 95° percentile dei massimi casuali.
Passa la verifica se: AUC verifica ≥ 0,60 sui 6 episodi, intervallo al 90% (ricampionamento degli episodi) con limite basso > 0,5, e AUC sulle sotto-finestre W2 (2-3 sedute) > 0,5.
Si riporta: anticipo tipico (mediana, fra gli episodi, delle sedute prima di t0 a cui la misura entra per la prima volta nel 10% più a rischio entro 20 sedute) e tasso di falsi allarmi (quota dei giorni di base con misura nel 10% più a rischio).
Risultato scritto in ESITO_ANTICIPO_CROLLI.md anche se negativo. Nessuna combinazione fra ipotesi viene provata in verifica (rischio di adattarsi): se più ipotesi passano, si propone solo un test in avanti.

## Limiti dichiarati
13 episodi (7+6), alcuni esterni; la soglia casuale è severa ma i dati sono pochi; il risultato è una prova di correlazione nel passato, non una previsione. Misure disponibili dal 2006 (put/call, struttura a termine del VIX) escluse per mancanza di episodi.
