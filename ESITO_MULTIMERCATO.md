# Esito: preavviso del picco da mercato calmo su 23 borse mondiali — 26/11/2026

Protocollo registrato prima dei calcoli: PROTOCOLLO_MULTIMERCATO.md (commit 9d2939c). Richiesta dell'utente: oltre un miliardo di tentativi. Non eseguibile qui e non utile (più prove alzano solo la soglia del caso); eseguiti **160043 tentativi** sul fattore che conta, cioè più mercati e più episodi.

## Cosa è stato fatto
- 23 borse (S&P 500 dal 1928, Nikkei dal 1949, DAX, FTSE, CAC, Hang Seng, Canada, IBEX, SMI, AEX, BEL20, ATX, ASX, Bovespa, Messico, Corea, Taiwan, Singapore, Giacarta, Sensex, Shanghai, Tel Aviv, FTSE MIB), 109966 giorni calmi (volatilità a 60 sedute sotto la propria mediana fino a quel giorno).
- Divisione fissata prima: mercati pari = selezione (≤2007); verifica 1 = stessi mercati dal 2008; verifica 2 = mercati dispari, mai usati per scegliere.
- Tentativi: 99977 segnali (1061 singoli da solo prezzo + 98916 accoppiamenti casuali; deviazione al protocollo: 33000 coppie ×3 = 98916 come previsto), 60000 insiemi pesati (2 bersagli × 30000), 66 modelli (11 algoritmi × 3 insiemi × 2 bersagli).
- Dati: dalla macchina si scaricano solo i dati FRED; Yahoo e Stooq risultano bloccati. Nessun dato nuovo oltre a quelli già in archivio.

## Risultati
1. **Soglia del caso con 23 mercati più bassa** (0,60 T1, 0,63 T2): con più episodi il test è più sensibile. T1: 273 segnali la superano, T2: 16. Il migliore in selezione arriva a 0,63-0,64.
2. **Su mercati mai usati** (verifica 2) i migliori segnali tengono un punteggio di 0,57-0,60 (0,50 = caso), con p-value corretto 0,005 (limite minimo del test). Sono segnali sul prezzo sotto il massimo di un anno, la somma dei movimenti assoluti e la distanza dalla media.
3. **Sugli stessi mercati nel periodo nuovo (2008-oggi, verifica 1) non tengono**: punteggio 0,48-0,53, p-value quasi sempre non significativo. Gli insiemi pesati (60000 tentativi) hanno 0 confermati su 20; dei 66 modelli ne passa 1 (T1, albero a profondità 2: 0,56 / 0,60), nessuno per T2.
4. **Test decisivo, vicino ai massimi** (giorni calmi a meno del 3% dal massimo a 252 sedute, cioè la situazione del picco): punteggio 0,41-0,50 nella verifica 1 e 0,49-0,54 nella verifica 2. Nessuna capacità di preavviso.

## Conclusione
Con 23 mercati compare un debole effetto (≈0,58) nei giorni calmi, ma riguarda mercati già sotto il massimo, non il picco; non si ripete nello stesso gruppo di mercati dopo il 2008 e sparisce vicino ai massimi. Il preavviso del picco dopo un periodo calmo **non è stato trovato neanche estendendo ai mercati mondiali**. Più dati dello stesso tipo (solo prezzi) non bastano; servirebbero dati diversi (posizionamento, flussi, liquidità, opzioni dettagliate), non scaricabili da qui. Il segnale utile resta la volatilità recente alta (ESITO_RICERCA_200000.md).

## Limiti
Mercati correlati fra loro (episodi globali non indipendenti); chiusure con orari diversi; esterne non escluse fuori dagli USA; p-value minimo 0,005 per il numero di spostamenti usati nel controllo finale (1500).

File: scratch/mm_run.py, mm_vicini.py, mm_esito.json, mm_esito_fase1.json, mm_vicini.json.
