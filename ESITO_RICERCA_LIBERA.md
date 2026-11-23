# Esito: ricerca libera di nuovi segnali di crisi finanziaria (23 novembre 2026)

Protocollo: PROTOCOLLO_RICERCA_LIBERA.md (pubblicato prima dei calcoli, commit 5d0ac8d). Script: scratch/ricerca_libera.py. Dati: scratch/ricerca_libera.json.

## Risultati
- 32 candidati, tutti valutabili. Soglia del caso (migliore su 32 idee, 95° percentile): AUC 0,8008.
- P1 (utile da solo): nessuno. Il migliore, D07, ha AUC di verifica 0,621 / 0,650 / 0,767 (una settimana / un mese / tre mesi), sotto la soglia del caso.
- P2 (migliora l'Indice crollo con peso 0,2): solo D07 «CAPE × prezzo sotto la media a 200 giorni». Guadagno in scelta +0,007 / +0,014 / +0,025, in verifica +0,002 / +0,013 / +0,049. Secondo controllo (togliendo 2001, 2002, 2008 uno alla volta): regge in tutti e tre i casi su 2 orizzonti.
- Singoli CAPE, P/E, Buffett: da soli non avvisano (AUC verifica 0,42–0,67, in scelta ≈0,5). Utili solo come contesto («caro» non dice «quando»).
- Salita del rendimento a 2 e 10 anni, CAPE × rendimenti: in scelta AUC sotto 0,5 (0,33–0,40) e in verifica sopra (0,68–0,74): segno che si inverte, quindi Non coerente.
- Tutti gli altri: Non coerente.

## Spia adottata (solo informativa)
«Mercato caro che sta già scendendo» = posizione storica del CAPE × quanto il prezzo è sotto la media a 200 giorni. Soglie fisse dal periodo fino al 2014 (80° e 90° percentile).
Con segnale acceso (top 19%), calo di almeno 8% entro 3 mesi: scelta 43,7% contro 10,9% senza; verifica (dal 2015) 38,7% contro 7,7%. Con soglia più alta (top 9%) la verifica scende a 27,4% contro 12,4%.
Oggi: acceso (livello «Forte»).

## Limiti e scostamento dal protocollo
- Esito: «Coerente con i casi osservati», non «provato». Non passa P1; i giorni accesi sono pochi episodi indipendenti (in verifica 416 giorni, pochi cicli: 2015-16, 2018, 2022).
- Misura la continuazione di un calo già iniziato: non anticipa il picco.
- Scostamento dichiarato: il protocollo prevedeva l'ingresso nell'Indice crollo a peso 0,2. Non l'ho fatto perché cambierebbe la scala su cui sono tarate le fasce (≤35, 36–40, …) e tutta la storia dei grafici. La spia è mostrata a parte in «Paura, protezioni e prezzi» senza toccare l'Indice crollo; la validazione continua dal vivo.
