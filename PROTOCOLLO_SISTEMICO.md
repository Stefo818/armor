# Protocollo Radar sistemico (MSA v3) — 21 novembre 2026
Origine: documento tecnico scritto da un altro assistente dopo il calo del 19-20 novembre. Il modello (regimi, soglie, pesi) è stato disegnato **conoscendo già gli episodi** (incluso novembre 2026), quindi i risultati "fuori campione" del documento non sono accettati come tali. Qui lo si prova UNA volta, esattamente come specificato, senza ritoccare nulla dopo aver visto i numeri.

## Cosa si prova
- Modulo `src/armor/modello_sistemico.py` come da specifica: 5 regimi con soglie fisse, 3 sensori veloci per regime, barometro rame/oro + dollaro, doppio orizzonte (`score_3m`, `score_6m`).
- **Booster opzioni NON incluso nel punteggio**: l'archivio delle opzioni ha solo 11 giorni (dal 11 novembre 2026), non c'è nulla da provare. Se mostrato, è solo informazione a parte.
- Dove un sensore non esiste ancora (VIX a 3 mesi dal 2006, VVIX dal 2007, banche regionali dal 2006, credito High Yield dal 2007, ecc.) la specifica lo riempie con valori fissi: lo dichiaro e provo anche il solo periodo 2008-2026, in cui quasi tutti i sensori esistono.

## Bersagli (S&P 500, chiusure, solo sedute con calo dal massimo a 252 sedute minore del 4%, dal 1997 a 126 sedute prima dell'ultimo dato)
- Y3 = nelle 63 sedute successive l'indice scende di almeno l'8% rispetto a oggi. Y6 = nelle 126 successive almeno il 10%.
- Principale: **escludendo gli shock esterni** (Y3 che inizia nel 1998-07-15/1998-10-31, nel 2020-02-01/2020-04-30, nel 2025-03-01/2025-04-30), coerente con l'obiettivo dell'utente (ribassi lenti). Secondaria: tutti i giorni.

## Confronti
`score_3m` e `score_6m` contro Indice Armor, Super Armor, percentile del VIX (solo passato) e regola «paura in salita» (B del PROTOCOLLO_FRAGILITA.md).

## Misure
AUC con intervallo al 90% (blocchi di 63 sedute, 1000 ripetizioni); AUC nelle due metà (1997-2011, 2012-2026); riferimento di caso: 500 spostamenti circolari (almeno 252 sedute) del punteggio contro il bersaglio, 95° percentile; episodi (Y3 raggruppati se a meno di 126 sedute): «intercettato» se `score_3m` ≥ 60 in almeno una seduta nelle 126 prima del giorno in cui il calo dal massimo arriva a −5%, con anticipo in sedute; precisione = P(Y3 | punteggio ≥ 60) contro la frequenza base; quota di sedute con punteggio ≥ 60.

## Regola dell'etichetta (fissata ora)
**«Coerente con i casi osservati»** solo se TUTTE vere: (1) AUC di `score_3m` sul principale ≥ 0,65; (2) limite basso dell'intervallo al 90% ≥ 0,55; (3) AUC ≥ 0,60 in entrambe le metà e nel solo 2008-2026; (4) AUC sopra il 95° percentile dei riferimenti di caso; (5) AUC di `score_3m` almeno 0,02 sopra quella dell'Indice Armor; (6) precisione ≥ 2 volte la frequenza base. Altrimenti **«Non coerente»**. Mai «provato».

## Cosa succede dopo
- Etichetta «Coerente»: scheda in Oggi sotto «Allerta vendite», con testo «non provato, pochi casi».
- Etichetta «Non coerente»: la scheda può comunque comparire come contesto («fotografia del regime»), senza avvisi sul telefono e senza dire che prevede.
- Il disaccordo tra i modelli del semaforo resta visibile (modifica solo di visualizzazione, non di previsione).
