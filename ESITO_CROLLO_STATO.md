# Esito: Crollo × Stato (25 novembre 2026)

Segue PROTOCOLLO_CROLLO_STATO.md (commit bbfc6d0, scritto prima dei calcoli). Script: scratch/crollo_stato.py, numeri completi in scratch/crollo_stato_esito.json.

## Risultato in una riga
Incrociare Crollo e Stato **non migliora** il Crollo da solo. Nessun punteggio supera il riferimento con intervallo al 90% che esclude lo zero, quindi non si adotta nulla. Verdetto: **Non coerente** con un miglioramento.

## Numeri (AUC in verifica dal 2015; differenza dal Crollo da solo con intervallo al 90%)
| Punteggio | Cala ≥3% in 5 sedute | Differenza | Cala ≥8% in 21 sedute | Differenza |
|---|---|---|---|---|
| X0 Crollo (media 5 sedute) | 0,796 | – | 0,847 | – |
| X1 Stato da solo | 0,597 | −0,31…−0,09 | 0,768 | −0,20…+0,12 |
| X2 prodotto | 0,765 | −0,12…+0,05 | 0,873 | −0,12…+0,20 |
| X3 minimo fra i due | 0,775 | −0,11…+0,05 | 0,868 | −0,09…+0,17 |
| X4 entrambi sopra 60 | 0,531 | −0,32…−0,20 | 0,548 | −0,38…−0,14 |
Soglia del caso (95° percentile del migliore su 5 con bersagli mescolati): 0,708 per i 5 giorni, 0,853 per i 21 giorni.

## Cosa si legge
- Sui **5 giorni** il Crollo da solo è il migliore. Lo Stato aggiunge rumore, non informazione.
- Sui **21 giorni** il prodotto e il «minimo fra i due» hanno un valore leggermente più alto (0,87 contro 0,85), ma la differenza è dentro l'errore e **nessuno, nemmeno il Crollo da solo, supera la soglia del caso (0,853)**. Indizio da seguire in avanti, non un risultato.
- Lo Stato da solo a 21 giorni (0,77) è sopra il caso semplice (0,5) ma sotto la soglia del migliore su cinque: coerente con l'idea «terreno fragile = più rischio nelle settimane», non dimostrata.
- La regola a doppia soglia (X4) è la peggiore: accendersi solo con entrambi sopra 60 toglie i casi giusti. Nei 102 giorni accesi dal 2015 il calo ≥3% è arrivato nel 12,7% dei casi contro il 6,3% normale; con il solo Crollo sopra 60 era il 17,1% (170 giorni).
- Oggi: Crollo 77 (media 5 sedute), Stato 56.

## Decisione
Nessun cambiamento ai pesi. Crollo, Minimi e Stato restano tre informazioni separate (peso zero per Stato e Minimi). X2 e X3 vengono registrati ogni giorno (data/indizi_registro.csv) per la prova in avanti sui 21 giorni.
