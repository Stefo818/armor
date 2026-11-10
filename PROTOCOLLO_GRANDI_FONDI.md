# Protocollo Grandi fondi (Patch 61-62), scritto prima di guardare i risultati

Scopo: capire se i movimenti dei grandi operatori anticipano i cali dell'S&P 500. **Peso zero** nelle previsioni, nei Saldi e nelle Opportunità finché non c'è una dimostrazione.

Segnali verificabili ora: crescita a 13 settimane delle attività dei fondi monetari USA (FRED WRMFNS); posizione netta, in % dell'open interest, di fondi a leva, gestori patrimoniali e dealer sui futures E-mini S&P 500 (CFTC, dal 2006).
Dati SEC (sec_dati.py, workflow «Grandi fondi (dati SEC)»): 13F (protezioni e quota in ETF indicizzati dei 50 maggiori fondi; pannello fissato dal trimestre PRECEDENTE; disponibile 46 giorni dopo la fine del trimestre), Form 4 (acquisti P su acquisti P + vendite S, 13 settimane), nuovi depositi Schedule 13D (13 settimane). Dalla rete dello sviluppo la SEC non era raggiungibile: i lettori sono provati su file finti con le colonne documentate e si fermano con un errore chiaro se le colonne reali differiscono (esecuzione «sonda» su GitHub).
Indicatori candidati del semaforo (candidati.py): curva del VIX (VIX3M/VIX), accelerazione della paura, distanza dalla media a 50 sedute; stessa regola. CMF non provato (mancano i volumi).

Regola: percentile mobile a 5 anni (solo passato); alto >= 80, basso <= 20; ritardo di pubblicazione 4 giorni (CFTC) e 2 (fondi monetari); bersagli: calo >= 5% entro 1 mese, calo >= 10% entro 3 mesi; confronto della frequenza dei cali tra segnale alto (o basso) e resto, intervallo al 90% con blocchi di ~63 sedute.
Un segnale è «dimostrato» solo se l'intervallo esclude lo zero, nella stessa direzione, in entrambe le metà della storia e su entrambi i bersagli. Con 4 segnali e 2 direzioni (8 test) un caso fortunato è possibile: un segnale dimostrato passa prima a un periodo in ombra di almeno 12 mesi prima di avere qualunque peso.
Registro giornaliero: data/grandi_fondi_badge_registro.csv (colonna peso = 0).
