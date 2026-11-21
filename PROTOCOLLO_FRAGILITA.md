# Protocollo Fragilità e sentinella (19 novembre 2026)
Scritto dopo il calo del 19 novembre (futures S&P 500 −1,4% nel giorno, −1,3% in 15 minuti attorno alle 18:00 ora italiana). Le tre regole sono state fissate UNA volta, prima dei numeri sotto, partendo dall'ipotesi dell'utente (media dei 200 giorni) e dalla paura (VIX) già usata da Armor. Nessuna variante provata.

## Regole (non cambiano dopo aver visto i risultati)
- **A** media 200 giorni appena rotta: l'indice chiude sotto la media da non più di 3 sedute.
- **B** paura in salita: VIX ≥ 22 e salito di almeno 10% in 5 sedute.
- **Terreno fragile** = A oppure B.
- **Vendite in corso** (sentinella, ogni minuto): futures −0,8% in 15 minuti, oppure VIX +10% in 15 minuti con VIX ≥ 20. Un solo avviso all'ora per tipo; «terreno fragile» al massimo ogni 12 ore.

## Prova storica (S&P 500 e VIX, 1990-2026, 9.089 giorni; bersaglio: calo di almeno 1,2% il giorno dopo)
| Condizione | Giorni | Calo ≥1,2% il giorno dopo |
|---|---|---|
| Tutti i giorni | 9.089 | 9,4% |
| A media rotta da poco | 344 | 13,1% |
| B paura in salita | 712 | 20,5% |
| A + B | 79 | 21,5% |
- Dei 857 giorni con calo ≥1,2%, solo il 25% aveva A, B o «sotto la media entro 2%» il giorno prima (quei segnali coprono il 14,6% dei giorni).
- Dopo i giorni con calo ≥1,2%: mediana a 20 sedute +2,0% (64% positive; tutti i giorni +1,2%, 64%).

## Lettura onesta
Il calo improvviso non si prevede: il segnale migliore (B) raddoppia la probabilità, da 1 su 11 a 1 su 5, e 4 volte su 5 non succede nulla. Serve a non essere colti di sorpresa, non a indovinare il giorno. La sentinella riduce il ritardo di reazione a pochi minuti, ma i prezzi gratuiti arrivano con 9-15 minuti di ritardo.

## Prova della sentinella sui prezzi del 19 novembre (scratch/sentinella_prova.mjs)
- Avviso «vendite forti» alle 18:04 ora italiana (futures −0,83% in 15 minuti), avviso «paura in salita» alle 18:09.
- «Terreno fragile» attivo già il 17 novembre (A e B vere; paura +31% in 5 sedute).

---
# Emendamento 1 (21 novembre 2026) — discesa a gradini, scritto PRIMA di contare i giorni di allarme
**Cosa è successo.** Venerdì 20 novembre l'S&P 500 ha perso il 3,7% ma senza un singolo movimento da 0,8% in 15 minuti (il massimo è stato −0,78%, per 0,02 punti sotto la soglia): la discesa è arrivata a gradini (−1,3% nell'ora delle 16:00 UTC, poi −0,5%, −0,5%, −0,9%, −0,5%). La paura è salita del 15,5% in un'ora ma non del 10% in 15 minuti. La sentinella non ha mandato un nuovo avviso di «vendite forti» (era già partito «terreno fragile» il 19).
**Regola aggiunta (scelta guardando venerdì: ammesso, è una taratura su un caso).** «Discesa a gradini» = futures S&P 500 −1,2% in 60 minuti, oppure paura +12% in 60 minuti con paura ≥ 22. Stesso blocco di un'ora per tipo.
**Regola di accettazione fissata ora, prima del conteggio.** Si conta in quanti giorni distinti degli ultimi 60 giorni di dati a 5 minuti (limite di Yahoo) la nuova regola sarebbe scattata. Se sono **al massimo 6** si adotta così; se sono di più si passa UNA volta a futures −1,5% / paura +15% e si adotta quella versione senza altri ritocchi.
