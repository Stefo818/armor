# Esito del protocollo «Crisi lente» (18 novembre 2026)

Regole: `PROTOCOLLO_CRISI_LENTE.md` (salvato prima di calcolare). Prove: `scratch/crisi_lente_prova.py`, risultati in `scratch/crisi_lente_risultati.json`. Esplorazione fatta dopo: `scratch/crisi_lente_esplorativa.py`. Modulo dell'app: `src/armor/crisi_lente.py`.

## Cosa si cercava
Uno strumento che avvisi quando sono probabili mesi o anni di sofferenza, non i cali da shock che si recuperano in fretta. Bersaglio: **crisi lenta** = calo di almeno 20% entro 2 anni e prezzo ancora sotto quello di partenza dopo 4 anni. Punteggio da 4 gruppi (valutazioni, credito, liquidità e tassi, economia), allarme «attenzione» sopra l'80° percentile della propria storia.
Nota: il 0,71 del controllo all'indietro viene quasi tutto dalle valutazioni (CAPE da solo 0,95).
Dati: 1.187 fine-mese dal 1928; 8 episodi di crisi lenta: 1929-32, 1934, 1936-40, 1946, 1966, 1973-74, 2000-02, 2007-09.

## Risultato (capacità di distinguere, 0,50 = moneta; controllo all'indietro 1928-52 / taratura 1953-89 / conferma 1990-2022)
| | 1928-52 | 1953-89 | 1990-2022 |
|---|---|---|---|
| Terreno lento | 0,71 | **0,58** | **0,89** |
| Solo valutazioni (CAPE) | 0,95 | 0,56 | 0,78 |
| Sotto la media a 10 mesi | 0,44 | 0,64 | 0,61 |
| 95° percentile dei sosia | 0,78 | 0,86 | 0,79 |
Intervalli al 90% del Terreno lento: 0,56-0,84; 0,41-0,83; 0,74-0,99. Mesi con crisi in corso (eventi su mesi validi): 89/300, 25/444, 38/394.
**Ogni periodo poggia su 2 o 3 episodi:** in taratura il 1966 e il 1973-74, in conferma il 2000 e il 2007-09.

## Allarme sopra l'80° percentile
- Conferma: mesi di crisi lenta segnalati 82%, falsi allarmi 22%; nel 28% dei mesi con allarme era in corso o stava per partire una crisi lenta, contro il 2% dei mesi senza allarme. Il solo CAPE: 79% e 45% di falsi allarmi.
- Taratura: 36% segnalati, 30% di falsi allarmi (7% con allarme contro 5% senza: nessuna differenza).
- Episodi: allarme acceso nei 24 mesi prima per 2000-02 (25 mesi su 25, 24 mesi di anticipo), 2007-09 (14 su 25, 13 mesi di anticipo) e 1966 (11 su 25); per il 1973-74 un solo mese di allarme isolato (non conta come segnale); mai per 1929, 1934, 1936, 1946.

## Verdetto per regola: «non superata»
Condizioni: (a) AUC ≥ 0,65 in taratura e conferma e ≥ 0,60 all'indietro: **no, 0,58 in taratura**. (b) batte il CAPE da solo e i sosia in conferma: sì (0,89 contro 0,78 e 0,79). (c) sensibilità ≥ 50% e falsi allarmi ≤ 25% in conferma: sì (82%, 22%). (d) allarme acceso prima di 2000 e 2007: sì. Poiché la taratura è sotto 0,60 non vale nemmeno «parziale»: etichetta **non utile** secondo la regola fissata prima.
**Controllo di specificità (Q) fallito:** il punteggio dovrebbe anticipare solo le crisi lente, invece ha anche capacità di anticipare i crolli rapidi poi recuperati (AUC 0,64 / 0,73 / 0,59, limite 0,55). Non distingue bene lento da veloce.
Lettura onesta: ha funzionato nelle due crisi lente degli ultimi trent'anni, non ha funzionato prima. Due casi non bastano per dire se sia una regola o un caso.

## Cosa c'era dentro (variabili singole, AUC in taratura / conferma)
Coerenti nel verso dichiarato in taratura e in conferma (ma curva, inflazione e salita dei tassi erano sotto 0,50 nel controllo all'indietro 1928-52: 0,33, 0,32, 0,36): tasso reale della banca centrale 0,76 / 0,91; debito privato in crescita su 5 anni 0,61 / 0,95; curva dei rendimenti (invertita) 0,59 / 0,86; inflazione 0,63 / 0,65; salita dei tassi a 3 mesi 0,69 / 0,63; valutazioni 0,56 / 0,78.
**Contrari al verso dichiarato, in entrambi i periodi:** crescita dei prestiti alle imprese 0,20 / 0,27, crescita della moneta M2 0,24 / 0,40, produzione industriale 0,18 / 0,45. Cioè prima delle crisi lente il credito, la moneta e la produzione erano in forte crescita, non in rallentamento. La mancanza di liquidità compare durante e dopo il crollo, non prima: l'ipotesi di partenza era sul verso sbagliato per gli indicatori di anticipo.

## Esplorazione fatta dopo (non è una prova: il segno si è visto dopo i risultati)
Se questi tre segnali di «boom» hanno il segno opposto (più prestiti, più moneta, più produzione = più rischio): AUC per le crisi lente 0,66 / 0,80 / 0,94; in conferma segnalati 89% con 13% di falsi allarmi; allarme acceso prima di 1966 (24 mesi), 2000 (24) e 2007 (8), non prima del 1973. Il controllo Q resta alto (0,70 / 0,71 / 0,61): non specifico. Va letto solo come ipotesi («le crisi lente seguono i boom di credito e moneta») da provare in avanti con una regola scritta prima.

## Stato di oggi (fine ottobre 2026)
Punteggio al 69° percentile: allarme spento. Valutazioni molto care (z +1,9) e debito privato in forte crescita (+1,6); credito, liquidità e tassi, economia nella norma. L'allarme si accende sopra l'80°.

## Cosa fa l'app
Scheda «4 · Crisi lente» in «Segnali di fondo», con stato dell'allarme, quattro gruppi in parole semplici, esito delle prove e tabella degli episodi. Peso zero: non entra in nessuna previsione. Registro mensile in `data/crisi_lente_registro.csv` per il giudizio in avanti.

## Limiti
Pochissimi episodi indipendenti; dati macro «come oggi»; prima del 1950 poche serie di credito; il periodo 1990-2022 era già stato guardato per altri bersagli (non vergine).
