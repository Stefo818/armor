# Protocollo «Indice Armor lungo» (scritto il 10/11/2026, PRIMA di guardare i risultati)

Domanda: l'Indice Armor, costruito guardando i dati dal 2000, funziona anche prima del 2000? Si prova una versione ridotta con soli ingredienti che esistono da molto prima, nel periodo 1950-1999 (prova su dati mai usati per costruirlo).

## Ingredienti (stessi pesi di famiglia dell'indice attuale, rinormalizzati sulle famiglie presenti)
- Paura e stress (22): volatilità dei prezzi a 21 sedute (al posto del VIX, che esiste dal 1990).
- Credito (18): spread BAA − titoli di Stato a 10 anni (dal 1953, soglie 2,1 / 2,8 come l'indice attuale); indice delle condizioni finanziarie di Chicago NFCI (dal 1971, soglie −0,2 / 0).
- Tassi (8): curva 10 anni − 3 mesi (dal 1953, soglie 0,5 / 0); rendimento a 10 anni (dal 1962, soglie 4 / 5).
- Valutazioni (12): CAPE (soglie 28 / 35); rapporto prezzo/utili (soglie 18 / 24).
- Tendenza dei prezzi (12): distanza dal massimo a 252 sedute (5 / 10); distanza dalla media a 200 sedute (0 / −5).
- Economia reale (6): regola di Sahm (0,3 / 0,5); produzione industriale sull'anno (3 / −3); nuove richieste di sussidio in aumento (15 / 25).
- Esclusi perché non esistono prima del 2000 o sono circolari: sentimento AAII, ampiezza, modello statistico Armor, VVIX, SKEW, MOVE, spread alto rendimento.
- Metodo identico all'indice attuale: punteggio 60% soglie + 40% percentile sugli ultimi 10 anni, media per famiglia, media pesata, scala 1–100. **In più**: ogni dato mensile o settimanale si usa solo dopo il suo ritardo di pubblicazione (nessuno sguardo al futuro).

## Misure
Indice di ieri contro tre eventi successivi: calo ≥5% in 21 sedute, calo ≥10% in 63 sedute (principale), volatilità ≥25% nelle 21 sedute successive. Misura: AUC (0,5 = a caso, 1 = perfetto). Periodi: 1950-1969, 1970-1989, 1990-1999 e, per confronto, 2000-oggi. Riferimento «solo prezzi»: media delle famiglie Paura e Tendenza.

## Regola di giudizio (fissata ora)
1. **Soglia**: AUC sul calo ≥10% a 63 sedute di almeno 0,62 in ciascuno dei tre periodi prima del 2000.
2. **Valore aggiunto**: l'indice lungo supera «solo prezzi» di almeno 0,02 in almeno 2 dei 3 periodi e non è sotto di più di 0,02 nel terzo.
3. **Tenuta dal 2000**: AUC 2000-oggi non più bassa di 0,05 rispetto all'indice attuale.
- Tutte e tre vere → **REGGE**. Solo 1 e 3 → **REGGE IN PARTE**. Altrimenti → **NON REGGE**.
- Conseguenze: se REGGE, si può scrivere un nuovo protocollo per rivedere i pesi su 1950-oggi (ancora nessun cambiamento automatico). Altrimenti l'indice resta com'è. Il risultato si pubblica sempre, anche se negativo.

## Limiti dichiarati
Mercato e dati cambiano nei decenni; i dati economici vengono rivisti (qui si usano le serie correnti, non quelle «come pubblicate allora»); gli episodi indipendenti sono circa 12–15. È una prova di robustezza, non una garanzia.

## Risultato (prima esecuzione, 10/11/2026) — scritto dopo, senza cambiare le regole sopra
Verdetto: **NON REGGE**. Soglia non superata (1950-1969: AUC 0,58 sul calo ≥10% a 3 mesi; 1970-1989: 0,66; 1990-1999: 0,65). Valore aggiunto sui soli prezzi: +0,03, +0,01, +0,02 (solo 1 periodo su 3 sopra 0,02). Tenuta dal 2000: 0,73 contro 0,73 dell'indice attuale (regola 3 rispettata).
Lettura: dopo il 2000 l'indice ridotto vale quanto quello completo, e i soli prezzi sono poco sotto: la gran parte del potere predittivo viene dai prezzi. Prima del 2000, e soprattutto nel 1950-1969, l'accuratezza è più bassa. Nessun cambiamento all'indice ufficiale; si ripete il calcolo ogni mese con i dati nuovi.
