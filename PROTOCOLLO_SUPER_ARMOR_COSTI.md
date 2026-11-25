# Protocollo: inflazione, petrolio e rialzo dei tassi nel Super Armor

Scritto il **25/11/2026 (pomeriggio)**, prima di calcolare un solo risultato. Nessuna regola si cambia dopo aver visto i numeri.

## Domanda dell'utente
Il Super Armor versione 2 (massimo fra pilastro finanza, 6 misure, e pilastro economia, 7 misure) **non contiene** inflazione, petrolio e aumento dei tassi. L'utente ritiene che abbiano un effetto importante sull'economia dei prossimi mesi. Si verifica se aggiungerli migliora il punteggio.

## Misure candidate (alto = peggio; percentile espandente, minimo 60 mesi; ritardi reali di pubblicazione)
- K1 Inflazione: prezzi al consumo (`cpi`), variazione su 12 mesi; ritardo 45 giorni.
- K2 Accelerazione dell'inflazione: variazione di K1 su 6 mesi; ritardo 45 giorni.
- K3 Petrolio: prezzo del greggio WTI (`wti`, dal 2000), variazione su 12 mesi; ritardo 1 giorno.
- K4 Rialzo dei tassi: tasso della Fed (`fedfunds`), variazione su 12 mesi; ritardo 1 giorno.
- K5 Rialzo dei tassi a 2 anni (`dgs2`), variazione su 12 mesi; ritardo 1 giorno.

## Varianti (N = 9, fissate ora; V0 = formula attuale, riferimento)
V0 = massimo(finanza, economia). Nuove: V1 = massimo(finanza, economia, **costi** = media di K1-K5) · V2 = K1-K5 aggiunte al pilastro finanza · V3 = K1-K5 aggiunte al pilastro economia · V4 = terzo pilastro con solo K1,K2 · V5 = terzo pilastro con solo K3 · V6 = terzo pilastro con solo K4,K5 · V7 = media dei tre pilastri (finanza, economia, costi) · V8 = 0,5 × massimo(finanza, economia) + 0,5 × costi.

## Bersagli e misure
Come PROTOCOLLO_SUPER_ARMOR_ECONOMIA.md: Z6 (economia a 6 mesi: disoccupazione, posti di lavoro, produzione, dati rivisti) con correlazione di Spearman; R6 (inizio recessione entro 6 mesi) con AUC. Campione comune: da quando tutte le misure esistono (petrolio: agosto 2006) a oggi. **Scelta: 2006-2014; verifica: 2015-2026.** Differenza Δ = misura(variante) − misura(V0) sugli stessi mesi. Intervallo al 90% di Δ con ricampionamento per anno (300 giri). Soglia «migliore fra N»: 200 spostamenti circolari del bersaglio (≥ 24 mesi), 95° percentile del massimo Δ fra le 8 varianti nuove, in verifica.

## Regola di giudizio
Una variante **entra nel punteggio del Super Armor** solo se: (a) Δ di Spearman > 0 in scelta e ≥ +0,05 in verifica; (b) estremo inferiore dell'IC90 di Δ in verifica > 0; (c) Δ di verifica ≥ soglia del migliore-fra-N. Altrimenti il punteggio resta V0.
Controllo del segno e del valore da sole: Spearman di ciascuna K1-K5 con Z6 su tutto il periodo disponibile (K1, K4, K5 dal 1992; K3 dal 2006) e nei due blocchi.
In ogni caso, K1-K5 entrano nell'app come **pilastro informativo «Costi e tassi» senza peso** (cliccabile, con grafico) e alimentano le indicazioni «flash» del Super Armor; il testo dichiara se sono «provati» o «non provati» nel punteggio.

## Limiti dichiarati
Verifica 2015-2026 con una sola recessione (2020, shock esterno) e un'inflazione anomala (2021-23); petrolio con storia breve (dal 2000); bersagli rivisti; mesi sovrapposti.
