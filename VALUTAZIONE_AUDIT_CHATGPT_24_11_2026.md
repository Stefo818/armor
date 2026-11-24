# Valutazione delle modifiche proposte da ChatGPT (24/11/2026)

## Cosa ha portato ChatGPT
1. `src/armor/bis_dsr.py` + test + blocco in `sources.py`: scarica dalla BIS il «peso del debito» (rata sul reddito) di famiglie e imprese.
2. `scratch/armor_endogenous_lab.py`: laboratorio che prova a prevedere cali (-8% in 63 giorni, -10% in 126, -15% in 252) con regressione logistica e alberi, camminando in avanti nel tempo.
3. AUDIT e prompt per Cowork: inventario dei dati, catalogo dei crolli interni, modello di rischio, architettura a 4 sottosistemi.

## Verdetto
- **Collector BIS: ADOTTATO, dopo correzioni.** Idea valida (debito privato = causa classica di crisi interne, dato senza sopravvivenza né revisioni di prezzo). Errori trovati: (a) il codice cercava la dimensione `REF_AREA`, ma per il DSR la BIS usa `BORROWERS_CTY`: dal vivo non avrebbe letto nulla; (b) `except: pass` nascondeva ogni errore; (c) nessuna data di disponibilità. Corretti: parser accetta entrambi i nomi, ogni richiesta fallita finisce in `data/status.json`, se non arriva nulla l'errore è esplicito, e `data/bis_dsr_meta.json` salva il giorno di prima vista di ogni trimestre (ipotesi prudente 150 giorni). Resta archivio a PESO ZERO. Test: 7 (prima 4, con dati finti non realistici).
- **Laboratorio: ADOTTATO come strumento esplorativo, NON come verità.** Si riproduce (45 combinazioni su 60 identiche; le altre 15 differiscono per il caso negli alberi). Ma mancava il confronto col caso. Aggiunto `armor_endogenous_placebo.py` (etichette spostate in modo circolare, «migliore su N prove»).
- **AUDIT/prompt: tenuti come riferimento, non eseguiti per intero.** Gran parte esiste già (protocolli pre-registrati, Indice crollo, laboratorio vivo, terreno). Spunti utili e già coperti: scoprire la data di pubblicazione dei dati (fatto per la BIS), segnalare i test con bias di sopravvivenza (le d_* non sono in produzione).

## Risultato del laboratorio con il placebo
Miglior abilità (Brier skill, >0 = meglio della frequenza storica) tra tutte le combinazioni:

| Orizzonte | Migliore reale | Migliore per puro caso (95°) |
|---|---|---|
| -8% in 63 giorni | 0,003 | 0,031 |
| -10% in 126 giorni | 0,007 | 0,145 |
| -15% in 252 giorni | -0,016 | 0,113 |

Il migliore reale è SOTTO la soglia del caso in tutti e tre. Quindi, sull'S&P 500 mensile da 2010/2015, nessun gruppo di variabili (prezzi, credito, cross-asset) prevede i cali meglio della frequenza media. Unica cifra positiva (VWCE proxy, 0,079) poggia su 4 eventi / 2 episodi: non valutabile (serve ≥6). Coerente con tutti gli esiti del giorno: l'unico effetto robusto resta «nessun segnale + indice fermo = meno cali» (clima, non segnale operativo).
Limiti dichiarati: 6 placebo per orizzonte (soglia grossolana, ma la conclusione regge con margine), campione di test piccolo (3-6 episodi).

## Decisioni
- Inserito: bis_dsr (peso zero) + aggancio in sources.py + test.
- Nessun indicatore nuovo nell'app: nessuna prova supera il caso.
- Dopo il primo giro dal vivo su GitHub Actions: controllare `data/status.json` (chiavi `bis_dsr_*`); quando ci saranno ≥30 anni di DSR, scrivere un protocollo (blocchi 1990-2004 / 2005-2020) PRIMA di testarlo.
