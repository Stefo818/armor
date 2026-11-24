# Esito: «convergenza di segnali deboli» (24/11/2026)
Regole: PROTOCOLLO_CONVERGENZA.md (commit 0da6f7b). Script `scratch/convergenza.py`, numeri `scratch/convergenza_esito.json`. Segnali: divergenza, salto rapido, indice alto con mercato forte (definizioni già fissate), conteggio nelle ultime 21 sedute.

## Verdetto: NON SUPPORTATO — la precisione NON sale con più segnali
- N≥1 (27% dei giorni): DR nel 2005-2020 quasi zero (+0,007 / +0,007 / +0,024), IC90 include 0.
- N≥2 (10% dei giorni, 12 episodi): bene nel 1990-2004 (+0,05 / +0,09 / +0,00) ma **nel 2005-2020 il segno si rovescia**: calo −8% 0% dopo il segnale contro 17% di base (IC90 sotto zero).
- N=3: solo 7 episodi, 2005-2020 non valutabile (23 giorni).
- Nessuna monotonia: più segnali non significano più rischio. Soglia del migliore fra 6: 0,25, mai raggiunta.
- Il controllo «nessun segnale e indice fermo» è invece di nuovo il dato solido: cali −8% in 63 sedute 11% e 14% contro 23% e 19% negli altri giorni (IC90 sotto zero nel primo blocco).

## Cosa si può trarre
Sommare segnali deboli non crea un segnale forte: erano in gran parte lo stesso fenomeno (mercato alto + indice in salita). Per la terza volta di fila, la sola cosa che regge in entrambi i blocchi è **l'assenza di segnali = clima più sicuro**. Nell'app nulla di nuovo.
