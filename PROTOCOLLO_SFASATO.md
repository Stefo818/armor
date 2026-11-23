# Protocollo: ricerca sfasata («il valore di ieri/della settimana scorsa prevede il dopo»)

Scritto e pubblicato prima di calcolare (23 novembre 2026, 13:05). Nessuna regola cambia dopo.

## Perché (domanda dell'utente)
Un indice che «va meglio con la paura» potrebbe solo seguire il prezzo. I confronti precedenti usavano il valore di oggi contro il calo dei giorni successivi (già sfasato di un giorno), ma includevano giorni in cui il mercato stava già scendendo: lì un indice alto «prevede» la continuazione di un calo già visibile. Qui si elimina quella scorciatoia e si prova TUTTO ciò che abbiamo.

## Solo crisi e correzioni finanziarie
Si escludono i giorni da 63 sedute prima a 60 dopo ogni shock esterno (lista ESTERNI) e da 5 prima a 180 dopo le due crisi miste (MISTE_MAX): così nessuna finestra di previsione contiene un evento esterno.

## Giorni valutati: «partenza da fermo»
Giorno t valutato solo se l'S&P 500 è entro il 5% dal massimo a 252 sedute E non è sceso più del 2% nelle ultime 5 sedute. L'indice non vede un calo già in corso.

## Tre eventi, sfasati e separati
- E1 (giorni dopo): nelle sedute t+1…t+5 il minimo è almeno −3% rispetto alla chiusura di t.
- E2 (settimane dopo): il minimo in t+6…t+21 è almeno −5% e in t+1…t+5 non si è arrivati a −3%.
- E3 (mesi dopo): il minimo in t+22…t+63 è almeno −8% e in t+1…t+21 non si è arrivati a −5%.
Sono eventi che arrivano DOPO un periodo senza calo: nessuna «continuazione».

## Candidati: tutto quello che abbiamo
Tutte le serie in data/series (tranne S&P 500 e suoi derivati diretti: sp500, sp_open, sp_high, sp_low, sp_vol, spy, vwce_de, vwce_ls, urth, vt, e il calcolo delle prove stesse). Per ogni serie 4 trasformazioni:
T0 livello, T5 variazione a 5 sedute, T21 variazione a 21, T63 variazione a 63; ognuna in percentile espanso (solo passato; minimo 252 sedute). Tutto il valore è quello di chiusura di t, con ritardo di pubblicazione fisso scelto dalla frequenza: giornaliera 1 giorno, settimanale 7, mensile 45, trimestrale 100. Le serie con copertura inferiore all'85% dei giorni valutati in scelta e in verifica sono escluse e contate.

## Selezione (una per evento) e soglia del caso
Il segno (più alto = più rischio o il contrario) si decide sul periodo di scelta (fino al 2014) e poi non cambia. Un candidato è «segnale» per un evento se:
AUC scelta ≥ 0,58 e AUC verifica (dal 2015) ≥ 0,58 con lo stesso segno, e AUC verifica sopra la soglia del caso: 95° percentile del migliore AUC di verifica su tutti i candidati con bersagli mescolati per anno (60 prove). Si dichiarano anche gli episodi indipendenti (eventi separati da 20 sedute) per periodo; se in verifica sono meno di 6, nessun candidato può essere «segnale» per quell'evento.

## Indice combinato
Per ogni evento, la media dei percentili (col segno scelto) dei «segnali» (al massimo i 10 migliori per AUC di scelta) = punteggio. Si confronta con l'Indice crollo attuale sugli stessi giorni (AUC scelta e verifica). Adozione: il combinato supera l'Indice crollo di almeno +0,03 in scelta e in verifica su almeno 2 eventi su 3 e non peggiora di più di −0,02 sul terzo. Se passa, diventa il nuovo Indice crollo (con scala 1–100 a percentili come ora). Esito: «Coerente con i casi osservati» / «Non coerente». Mai «provato».

## Emendamento 1 (23 novembre 2026, 13:20, prima di calcolare con i nuovi dati): serie nuove da Yahoo Finance
La richiesta: usare subito più dati. I dati «veloci» (opzioni a breve scadenza, flussi intraday) non hanno storia disponibile; si aggiungono invece serie giornaliere gratuite con storia lunga, scaricate il 23 novembre.
Nuove serie: ^VXN, ^VXD, ^OVX, ^GVZ, ^VIX9D, ^TNX, ^FVX, ^IRX, ^TYX, LQD, JNK, TLT, SHY, EMB, MUB, KBE, IYR, ^RUT, ^SOX, ^NYA, JPY=X, CHF=X, AUDUSD=X, ^HSI, ^KS11, ^FTSE, ^FCHI, XLY, XLP, SPLV, USMV, MTUM, QQQ, IWD, IWF, ^VIX3M, ^VIX6M, GLD. (Non scaricabili: ^RVX, ^VXEEM.)
Rapporti fissati ora: LQD/TLT, JNK/LQD, KBE/S&P 500, ^VXN/VIX, ^VIX9D/VIX, ^VXD/VIX, IWD/IWF, XLY/XLP, QQQ/S&P 500.
Stesse 4 trasformazioni, stessi eventi, stesso perimetro. Regola di copertura per le nuove serie: almeno 8 anni di giorni valutati nel periodo di scelta e copertura ≥85% dalla loro prima data; le date mancanti all'inizio contano come neutre (rango 0,5), quindi penalizzano e non favoriscono. La soglia del caso si ricalcola su vecchi e nuovi candidati insieme (stesso seme). Tutte le altre regole, compresa l'adozione, restano identiche.
