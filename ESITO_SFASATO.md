# Esito: ricerca sfasata (23 novembre 2026)

Protocollo: PROTOCOLLO_SFASATO.md (commit 327687e, scritto prima dei calcoli). Script: scratch/sfasato.py. Dati: scratch/sfasato.json.

## Risposta alla domanda dell'utente
Le prove precedenti erano già sfasate (il valore del giorno t contro il calo dei giorni successivi), ma includevano giorni in cui il mercato stava già scendendo: lì un indice alto «prevede» la continuazione di un calo già visibile. In questa prova si valutano solo giorni «partenza da fermo» (S&P entro il 5% dal massimo e senza calo di più del 2% nelle ultime 5 sedute) e tre eventi separati: E1 calo di almeno 3% nei 5 giorni dopo; E2 calo di almeno 5% fra 6 e 21 giorni dopo, senza calo prima; E3 calo di almeno 8% fra 22 e 63 giorni dopo, senza calo prima. Perimetro finanziario: tolti da 63 sedute prima a 60 dopo ogni shock esterno.

## Risultati (396 candidati con copertura sufficiente, su 684 testati: 200 serie × 4 trasformazioni)
- Episodi indipendenti (scelta/verifica): E1 47/13, E2 30/8, E3 12/3. E3 non è valutabile in verifica (3 episodi).
- E1 (giorni dopo): soglia del caso 0,737. Un solo segnale supera tutte le regole: il livello del VIX (paura), AUC scelta 0,691, verifica 0,784. Seguono variazione del CAPE a 5 giorni (0,705), condizioni finanziarie (rischio) 0,697, tassi della banca centrale, P/E: sotto la soglia del caso.
- E2 (settimane dopo): soglia del caso 0,843; nessun candidato la supera (migliori 0,77: condizioni finanziarie, premio al rischio, insoluti dei mutui).
- E3 (mesi dopo): soglia 0,973 con soli 3 episodi in verifica; AUC alti (0,90–0,92) su serie come recessione o spread del credito sono artefatti di 3 episodi, non risultati.
- Indice combinato dei segnali (per E1 è solo il VIX) contro l'Indice crollo attuale: E1 scelta 0,703 contro 0,677 e verifica 0,784 contro 0,759 (+0,026 e +0,025, sotto +0,03); E2 e E3 senza segnali. Adozione: no. Etichetta: «Non coerente».

## Lettura
- Anche partendo da mercati fermi, l'Indice crollo anticipa i cali dei 5 giorni successivi meglio del caso (AUC 0,68 scelta, 0,76 verifica). Non è solo uno specchio del prezzo, ma è un anticipo moderato: lascia passare molti cali.
- Il segnale più forte per i prossimi giorni è proprio il livello di paura, quando il mercato non sta ancora scendendo. Togliere la paura lo peggiora (vedi emendamento 1 di ESITO_ANTICIPO.md).
- Per settimane e mesi dopo, con i pochi episodi disponibili, nessuna delle 396 variabili supera la soglia del caso. Valutazioni, credito e tassi dicono se il terreno è fragile, non quando.

## Limiti
Pochi episodi in verifica (13, 8, 3). Molti test (396 × 3): la soglia del caso serve a questo. Serie con copertura breve (hy_oas, breadth) escluse. Nessuna regola è stata cambiata dopo i risultati. L'Indice crollo non viene modificato.

## Emendamento 1: nuove serie Yahoo (script scratch/sfasato2.py, dati scratch/sfasato2.json)
Scaricate 39 serie giornaliere (paure di altri indici, credito e obbligazioni, banche, valute, borse estere). Con la regola «almeno 8 anni nel periodo di scelta» ne sono entrate in prova 12 (^TNX, ^FVX, ^IRX, ^TYX, ^RUT, ^NYA, ^SOX, ^HSI, ^KS11, ^FTSE, ^FCHI, JPY=X); le altre, con storia più breve (VXN, VXD, OVX, GVZ, JNK, LQD, TLT, SHY, EMB, KBE e i rapporti che le usano), non hanno abbastanza storia per la prova del passato.
Esito: invariato. Soglie del caso identiche (0,737 / 0,843 / 0,973); E1 ancora solo il livello del VIX; nessun nuovo segnale; nessun candidato adottabile («Non coerente»). Un valore apparentemente alto (^FVX livello, E3: verifica 0,929, scelta 0,510) è l'artefatto dei 3 soli episodi di verifica.
Le serie con storia breve sono state aggiunte al download giornaliero (src/armor/sources.py): da oggi si accumulano per una prova in avanti.
