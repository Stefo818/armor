# Esito: «Indice Armor in salita mentre il mercato sale» (24/11/2026)
Regole: PROTOCOLLO_DIVERGENZA.md (commit 39a8ecb). Prova su 1990-2020, blocchi 1990-2004 e 2005-2020; script `scratch/divergenza.py` (+ `scratch/divergenza_cattura.py`, esplorativo), numeri in `scratch/divergenza_esito.json`.

## Verdetto formale: NON SUPPORTATO
Mercato in salita vicino ai massimi: frequenza di base dei cali 9,6% (−8% in 63 sedute), 10,3% (−5% in 21), 11,4% (−10% in 126). Stati D1 (indice +6 punti in 42 sedute), D2 (+4 in 21), D3 (indice ≥ 45):
- Nessun IC90 positivo in entrambi i blocchi; segni instabili (D1: −5% in 21 sedute +0,07 e +0,14, ma gli intervalli includono 0; per −8% a 63 e −10% a 126 il segno cambia o è negativo). D3 nel 2005-2020 ha solo 26 giorni (non valutabile).
- Soglia del migliore fra 9: 0,37; nessuno la raggiunge.
- Rispetto al controllo K (indice fermo o in calo con mercato forte) il segno è positivo quasi sempre (+0,01 / +0,19): l'indice in salita è un po' peggio dell'indice fermo.

## Cosa c'è di vero: l'osservazione regge come SENSIBILITÀ, non come precisione (esplorativo)
- **Dei 9 picchi endogeni del 1990-2022, lo stato D1 era acceso nelle 126 sedute precedenti in 7**, D2 in 7, D3 in 6. Per caso (stato spostato in modo circolare, 1.000 prove) se ne prendono in media 2,8-3,3: p = 0,002, 0,01, <0,001. Lo stato è acceso solo il 2-5% dei giorni.
- **Ma i segnali non sono seguiti dal calo più spesso del normale**: i 14-15 episodi D1/D2 del 1990-2020 portano al calo −10% in 126 sedute nel 9-17% dei casi, contro 11-22% di base. Alta copertura dei crolli, bassa precisione: molti segnali, pochi crolli. Il tempo fra segnale e picco è lungo e variabile (anche mesi), quindi non serve come allarme.
- **L'altro lato è più chiaro**: con mercato forte e indice fermo o in calo (K, 33-39% dei giorni) i cali sono quasi dimezzati (−8% in 63 sedute 8% e 10% contro 21% e 19% negli altri giorni; IC90 sotto 0 in 4 casi su 6). È la lettura «mercato sano e tranquillo», in buona parte momentum.
- 2021-2026 (descrittivo): D1 si è acceso 4 volte (ago 2021, ago 2024, nov 2025, ott 2026 in corso), D2 5 volte; il calo −8% a 63 sedute è arrivato solo dopo il dic 2021 (−11%); ago 2021, ago 2024 e nov 2025 no. Oggi nessuno stato è acceso (l'indice è 54 con il mercato −7% dai massimi: non più «mercato forte»).

## Cosa si può trarre
L'Indice Armor che sale con il mercato alto è spesso nel prologo dei grandi picchi, ma **non basta a dire che il calo è vicino**: l'avvertimento è «attenzione, il terreno si fa meno solido», non «tra poco crolla». Nell'app resta com'è: nessun avviso nuovo. Una lettura possibile (da provare con un protocollo a parte): indice fermo o in calo con mercato forte = clima più sicuro. Anche per questo il registro dell'Indice Armor è già salvato ogni giorno.
