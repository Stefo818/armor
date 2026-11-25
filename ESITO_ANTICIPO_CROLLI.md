# Esito: cosa precede un crollo improvviso (≥ 8% in 5 sedute) — 25/11/2026

Protocollo: PROTOCOLLO_ANTICIPO_CROLLI.md (commit 2f85d9e, prima dei calcoli). Script: scratch/anticipo_crolli.py; dati: scratch/anticipo_crolli_esito.json.
13 crolli dal 1990 (1997, 1998, 2000, 2001, 2002, 2008, 2011, 2015, 2018, 2020, 2022, 2025, 13/11/2026). 102 ipotesi.

## Parte 1: Indice Crollo prima dei crolli
- Sopra 60 per la prima volta (entro 60 sedute): 1997, 1998, 2000, 2001, 2002, 2008, 2022 → 53-60 sedute prima (già alto da quasi 3 mesi); 2015 (34), 2025 (21), 2020 (13), 2026 (6) → poco prima; 2011 e 2018 → mai.
- Valore 2 sedute prima: ≥ 85 in 1998, 2000, 2001, 2002, 2008, 2022; 17-27 in 2015, 2018, 2020 (crolli partiti da mercati calmi).
- Capacità di separare i giorni prima del crollo dai giorni normali (AUC pesata per episodio, 0,5 = caso): Crollo 0,69; Armor 0,76; Minimi 0,73.
- Quindi la media bassa deriva dal mix: indice alto e ben in anticipo in circa metà dei crolli, ma non vede i crolli partiti a mercato calmo (2015, 2018, 2020).

## Parte 2: ipotesi (selezione = 7 episodi fino al 2011, verifica = 6 dal 2015)
- Soglia contro il caso (massimo fra 102 ipotesi su date spostate a caso, 95°): AUC 0,868; mediana 0,737. **Nessuna ipotesi la supera: nessuna passa le regole del protocollo.**
- Ipotesi dell'utente (mercato fermo vicino ai massimi, rotture fallite, ombre superiori): AUC 0,28-0,50. Prima dei crolli improvvisi il mercato **non** è fermo sui massimi: succede meno del normale. Già i giorni prima, calo/massimi decrescenti (AUC 0,61), nuovi minimi a 20 giorni (0,71).
- Gruppo coerente (AUC ≥ 0,60 in entrambe le metà): volatilità che si allarga. Migliori, su tutti i 13 episodi:
  - VIX sopra la sua media a 60 giorni: 0,725 (selezione 0,74, verifica 0,71); 2-3 sedute prima 0,78; segnale in 10 episodi su 13, anticipo mediano 11,5 sedute.
  - Ampiezza media giornaliera (massimo-minimo) a 5 giorni su 60: 0,72; 2-3 sedute prima 0,75; 10/13, anticipo 17,5.
  - Massimo del VIX a 10 giorni su media 60: 0,71; volatilità a 10 su 60 giorni: 0,70.
  - Altri: variazione a 20 giorni del differenziale Baa (0,73, ma solo 5/13 con segnale), nuovi minimi a 20 giorni (0,71), Nikkei a 20 giorni in calo (0,68).
- Inefficaci: calendario (agosto-ottobre, scadenze), correlazione fra settori, livello del credito, CISS, volume, posizione della chiusura.

## Limiti
13 episodi (includono 11 settembre e Covid; senza 2001 e 2020 i risultati cambiano poco); i segnali del gruppo volatilità avvisano ma suonano anche in altri momenti (per costruzione il 10% dei giorni); AUC 0,7 = utile ma lontana da una previsione sicura; i crolli partiti a mercato calmo (2015, 2018, 2020) non sono visti da nessuno strumento. Test in avanti consigliato prima di cambiare l'indice.
