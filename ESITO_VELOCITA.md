# Esito: «velocità dell'Indice Armor» (24/11/2026)
Regole: PROTOCOLLO_VELOCITA.md (commit cafa180). Prova su 1990-2020, blocchi 1990-2004 e 2005-2020; script `scratch/velocita.py`, numeri in `scratch/velocita_esito.json`.

## Verdetto: INDIZIO DEBOLE (non dimostrato)
Stato V1 = indice +10 punti in 10 sedute restando sotto 60 (3% dei giorni, 22 episodi indipendenti). Basi di calo: −8% in 63 sedute 16,6%; −5% in 21 sedute 15,7%; −10% in 126 sedute 20,9%.
- Il segno è positivo in tutti e 6 i casi (3 bersagli × 2 blocchi): cali dopo V1 al 19-25% contro 16-22%. Per la regola scritta è un «indizio».
- Ma l'effetto è piccolo (DR da +0,01 a +0,08) e **tutti gli intervalli al 90% includono lo zero**; il DR 2005-2020 (0,03 / 0,05 / 0,01) è lontano dalla soglia del migliore fra 9 (0,20). Contro il controllo K (indice fermo, sotto 60) il segno è netto (+0,08/+0,14), ma K è il caso più tranquillo: lì i cali sono la metà del normale.
- Picchi endogeni catturati nelle 126 sedute prima: 7 su 9, ma per caso se ne prendono 5,6 (p = 0,27): nessuna informazione in più. A differenza della divergenza, qui la copertura non è speciale.
- V2 (+15 punti) e V3 (salto da calma): troppo rari (0,3% e 0,1% dei giorni, 9-15 giorni per blocco): non valutabili.

## 2021-2026 (solo descrittivo)
V1 acceso 8 volte; sulle 7 valutabili il calo −8% a 63 sedute c'è stato 3 volte (nov 2021 −8,0%, ago 2022 −11,8%, mar 2025 −14,8%); nelle altre (mag 2021, mar 2023, ago 2024, mar 2026 −5,9%) no o meno. 3 su 7 contro 17% di base: sopra il caso, ma sono pochi casi e sono quelli da cui nasce l'ipotesi. Il 16/10/2026 si è riacceso: episodio in corso. Oggi nessuno stato è acceso.

## Cosa si può trarre
La velocità è la lettura più vicina a un segnale fra le tre provate, ma regge solo come tendenza lieve: **un salto rapido dell'indice è un motivo di attenzione, non un allarme**. Decisione: nulla nell'app per ora, nonostante la regola prevedesse per l'indizio una riga informativa: con DR ≤ 0,05 e intervalli che includono lo zero la riga darebbe più sicurezza di quella che i numeri danno. Verifica in avanti: l'indice è salvato ogni giorno in `data/titan_storia.csv`, quindi V1 si può ricontrollare tra qualche mese senza nuovi dati.
