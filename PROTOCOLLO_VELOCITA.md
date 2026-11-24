# Protocollo «velocità dell'Indice Armor» (scritto il 24/11/2026 ore 16:10, prima di calcolare)

## Domanda
Non conta il livello dell'indice né la salita lenta (già provate: non supportate), ma **quanto in fretta sale in pochi giorni**. Un salto rapido, mentre l'indice è ancora sotto 60 (non ancora rosso), anticipa un calo?

## Disegno
Prova su **1990-2020**, blocchi 1990-2004 e 2005-2020 (devono reggere entrambi); 2021-2026 solo descrittivo. Indice: `armor_tarato`. Stesse esclusioni di shock esterni (ESTERNI, MISTE_MAX, 17/10/1973), stessi episodi indipendenti (distanza 126 sedute), soglia «migliore fra N» con 500 spostamenti circolari sul 2005-2020. Limite: la taratura dell'indice è fatta sulla storia intera.

## Stati (fissati ora)
Sia a l'indice del giorno e a10 = indice di 10 sedute prima.
- **V1 salto rapido**: a − a10 ≥ 10 punti e a < 60.
- **V2 salto molto rapido**: a − a10 ≥ 15 punti e a < 60.
- **V3 salto da calma**: a − a10 ≥ 10 punti e a10 < 35.
- **K controllo**: a < 60 e a − a10 compreso fra −3 e +3.

## Bersagli
T2 calo −8% entro 63 sedute; T3 calo −5% entro 21 sedute; T5 calo −10% entro 126 sedute (S&P 500).

## Giudizio
Come per la divergenza. **Dimostrato**: per almeno 2 bersagli su 3 IC90 > 0 (bootstrap per anno, 400 giri) in entrambi i blocchi, DR 2005-2020 ≥ soglia del migliore fra 9, ≥ 6 episodi indipendenti e DR > 0 contro K. **Indizio**: DR > 0 in entrambi i blocchi su ≥ 2 bersagli. Altrimenti **non supportato**. In più (esplorativo): quanti dei 9 picchi endogeni (1990-07-16, 1997-10-07, 1998-07-17, 2000-03-24, 2007-10-09, 2010-04-23, 2011-04-29, 2018-01-26, 2022-01-03) hanno lo stato acceso nelle 126 sedute prima, contro il caso (1.000 spostamenti).
## App
Dimostrato: avviso informativo «l'indice sta salendo troppo in fretta». Indizio: solo riga informativa. Non supportato: nulla.
