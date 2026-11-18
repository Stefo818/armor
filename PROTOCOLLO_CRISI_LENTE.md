# Protocollo «Crisi lente» (scritto il 18 novembre 2026, PRIMA di calcolare qualunque risultato)

## Perché un nuovo protocollo
Il protocollo «Terreno» misurava qualunque calo (≥10% in 6 mesi, ≥15% in 12). Includeva anche i cali da shock esterno (Covid, dazi, guerre), che si recuperano in fretta e che nessuno si aspetta di prevedere. Richiesta dell'utente: uno strumento che dica «attenzione: sono probabili mesi o anni difficili, di sofferenza e stagnazione» (come 2000-2013), cioè le crisi da liquidità, credito ed economia in difficoltà, che si recuperano lentamente. Non i cigni neri.

Limite da sapere prima: in 95 anni di dati ci sono solo circa 6-7 crisi lente vere. Qualunque risultato poggia su pochi episodi e va letto con cautela.

## Bersaglio (S&P 500, chiusure giornaliere dal 1927, prezzo senza dividendi)
Alla fine di ogni mese t:
- **Crisi lenta (L)** = calo massimo di almeno 20% entro 504 sedute (24 mesi) **e** prezzo a 1008 sedute (4 anni) ancora sotto il prezzo di t. «Il mercato crolla e dopo quattro anni non ha ancora recuperato».
- **Stagnazione (S)** = prezzo a 756 sedute (3 anni) sotto quello di t.
- **Controllo, shock recuperato (Q)** = calo massimo ≥20% entro 24 mesi, ma prezzo a 4 anni sopra quello di t (1987, 2020, 2022 e simili). Il nostro punteggio non dovrebbe anticiparli: si riporta come prova di specificità.
Gli esiti si conoscono solo a maturazione (4 anni). Ultima data valutabile: ottobre 2022.

## Il punteggio «Terreno lento» (segni e ritardi fissati ora; più alto = più rischio di crisi lenta)
Quattro gruppi, ogni variabile standardizzata sul solo passato (media e deviazione espandibili, minimo 48 mesi, tagliata a ±4), punteggio di gruppo = media delle variabili disponibili, punteggio finale = media dei gruppi disponibili (almeno 3 su 4). Nessun peso scelto sui dati.
- **V. Valutazioni**: CAPE (logaritmo, +, ritardo 0).
- **K. Credito**: spread BAA meno AAA (+, 1); crescita dei prestiti alle imprese a 6 mesi (−, 1); variazione a 5 anni del debito privato rispetto alla ricchezza (+, 5).
- **L. Liquidità e tassi**: variazione a 12 mesi del tasso a 3 mesi (+, 1); curva 10 anni meno 3 mesi (−, 1); crescita annua della moneta M2 (−, 2); tasso reale della banca centrale (+, 1).
- **M. Economia**: crescita annua della produzione industriale (−, 1); variazione a 12 mesi della disoccupazione (+, 1); inflazione annua (+, 1).
Prima del 1953-1960 alcune serie mancano: il punteggio usa quelle disponibili (regola dei 3 gruppi su 4).

## Periodi
- **Controllo all'indietro 1928-1952** (solo serie disponibili allora: CAPE, spread BAA-AAA, tasso a 3 mesi, produzione industriale, inflazione): vale per i casi del 1929 e del 1937.
- **Taratura 1953-1989.**
- **Conferma 1990-2022, guardata una volta sola.** Nota di onestà: questo periodo è già stato guardato per altri bersagli (protocollo Terreno): non è vergine.

## Misure
1. Capacità di distinguere (AUC) del punteggio per L e per S, in ciascun periodo, con intervallo al 90% a blocchi di 36 mesi.
2. Confronto con due alternative semplici: **CAPE da solo** (le valutazioni) e **tendenza** (prezzo sotto la media a 10 mesi, già in sofferenza). Il Terreno lento «aggiunge» qualcosa solo se in conferma batte il CAPE da solo.
3. **Allarme «attenzione»** = punteggio sopra l'80° percentile della propria storia (solo passato, minimo 10 anni). Misure: quota di mesi di allarme quando L=1 (sensibilità), quota di mesi di allarme quando L=0 (falsi allarmi), frequenza di L con e senza allarme.
4. **Episodi**: gli episodi sono i gruppi di mesi con L=1 separati da più di 12 mesi. Per ciascuno si riporta se l'allarme era acceso almeno un mese nei 24 mesi prima del primo mese con L=1, e con quanti mesi di anticipo.
5. **Prova del sosia**: 200 punteggi costruiti con lo stesso metodo da serie di rumore; il punteggio vero deve superare il 95° percentile in conferma.
6. Controllo Q: l'AUC su Q non dovrebbe superare 0,55 (non deve anticipare gli shock).

## Etichetta (regola fissata ora)
- **Utile**: AUC per L ≥ 0,65 in taratura e in conferma e ≥ 0,60 nel controllo all'indietro; in conferma batte il CAPE da solo e il 95° dei sosia; allarme 80° con sensibilità ≥ 50% e falsi allarmi ≤ 25% in conferma; allarme acceso prima di ciascun episodio della conferma (2000 e 2007).
- **Parziale**: AUC ≥ 0,60 in taratura e conferma ma non tutte le altre condizioni.
- **Non utile**: gli altri casi.
Se «utile»: nell'app compare l'avviso «attenzione: aumentano i rischi di mesi difficili», con le lead time storiche e i falsi allarmi. Se «parziale»: scheda di contesto con la dicitura «da solo non basta». Se «non utile»: scheda informativa, dichiarato.
Nessun numero, segno o soglia si cambia dopo aver visto i risultati.

## Limiti
Circa 6-7 episodi in tutto, 2 in conferma. Dati macro «come oggi» (revisioni possibili). Il CAPE e i prezzi sono già noti al mercato: un buon risultato non è un'operazione garantita.
