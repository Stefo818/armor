# Esito Crisi lente 2 (due chiavi, dal 1990)
Protocollo: PROTOCOLLO_CRISI_LENTE_2.md (+ Emendamento 1, scritto prima di leggere i risultati). Script: scratch/crisi_lente2_prova.py. Numeri: scratch/crisi_lente2_risultati.json.

## Verdetto secondo la regola scritta prima: **non coerente**
La regola chiedeva tutte e quattro: allarme (80°) acceso prima di ogni caso, falsi allarmi ≤ 25%, AUC ≥ 0,70, AUC sopra il 95° dei sosia. Esito: allarme prima di ogni caso **no**; falsi allarmi 1% sì; AUC 0,78 sì; sopra i sosia (0,71) sì. Una condizione su quattro fallita = "non coerente". Soglie non modificate dopo il risultato.

## Numeri (252 mesi 1995-2026 non ancora in crisi, 55 mesi "prima di un ribasso lento")
- Ribassi lenti dal 1990 (≥15%, ≥18 mesi dal massimo al recupero): 2000-2007, 2007-2013, 2022-2024. Esclusi come rapidi: 1990, 1998, 2018, 2020, 2025.
- AUC punteggio 0,78 (intervallo 90%: 0,66-0,89). Chiave 1 0,72; Chiave 2 0,53; solo Boom 0,78; solo Shock 0,64; solo valutazioni 0,60; tendenza 0,43. Sosia: mediana 0,49, 95° 0,71, massimo 0,79.
- Allarme a 80°: mai acceso (sensibilità 0%). A 65° (livello "attenzione", dichiarato nel protocollo): sensibilità 20%, falsi allarmi 12%, 13% del tempo.
- Per caso, nei 24 mesi prima: bolla internet 7 mesi su 25 sopra 65° (dal 1996-09, massimo 0,72); crisi finanziaria 4 su 25 (dal 2005-03, massimo 0,70); 2022 0 su 25 (massimo 0,59).

## Lettura onesta
- Il punteggio è più alto del solito prima dei due casi grandi, ma non abbastanza da superare la soglia d'allarme: segnale debole, non una sirena.
- Il lavoro lo fa la chiave 1 (credito facile + tassi), soprattutto il Boom. La chiave 2 (stretta) da sola non distingue (0,53): arriva quando la crisi è già iniziata.
- 2022 non è stato anticipato: i tassi sono saliti, ma il credito non era "facile" abbastanza per i percentili dal 1990.
- Tre casi non provano nulla. La definizione del bersaglio è stata corretta dopo un primo tentativo degenerato (1 solo mese positivo): documentato nell'Emendamento.
- Oggi (fine ottobre 2026): punteggio 72°, chiave 1 72°, chiave 2 38°, valutazioni al 96° (contesto). Livello "attenzione", non allarme.

## Cosa è in produzione
Scheda "4 · Ribassi lenti: due chiavi" con etichetta "non provata". Registro mensile in data/crisi_lente_registro.csv: giudizio in avanti.
