# Esito: indice di fase «verso il minimo / lontano dal minimo» (25 novembre 2026)

Segue PROTOCOLLO_MINIMI_5.md (commit 85c0f55, scritto prima dei calcoli). Script scratch/minimi_5.py, numeri in scratch/minimi_5_esito.json. Il Protocollo 4 non è stato concluso (calcolo interrotto, nessun risultato visto) ed è sostituito dal 5.

## Risultato in una riga
Con il bersaglio giusto («in questa discesa il minimo è ancora davanti o già alle spalle?») un punteggio **funziona** nei 14 mercati e sul solo S&P 500, solo crisi interne. Criteri di adozione tutti superati da E1 (modello + cinque segnali semplici): adottato come nuovo Minimi. Verdetto: **Coerente con i casi osservati**.

## Numeri
Giorni valutati: 25.464 in 284 discese di 14 mercati (previsioni fuori campione dal 2000, shock esterni esclusi). Base: 50,9% giorni «fondo davanti». Soglia del caso (95° percentile del migliore su 5): 0,582.
| Punteggio | AUC | IC90 | Discese con AUC > 0,5 |
|---|---|---|---|
| N1 durata (sedute dal massimo) | 0,577 | 0,53–0,63 | 142/162 |
| N2 rimbalzo dal minimo (ingenuo di prezzo) | 0,710 | 0,69–0,73 | 151/162 |
| L1 modello addestrato | 0,741 | 0,71–0,77 | 143/162 |
| L3 cinque segnali semplici | 0,731 | 0,71–0,75 | 131/162 |
| **E1 media di L1 e L3** | **0,765** | 0,74–0,79 | 143/162 (88%) |
Solo S&P 500 (18 discese): B0 (vecchia «svolta» invertita) 0,772; N2 0,780; L3 0,778; E1 0,768; L2 (con paura, credito, settori) 0,750; L1 0,674. Su ogni mercato l'AUC di E1 è sopra 0,5 (14 su 14 per L1 e L3).
Criteri: (a) sopra la soglia, limite inferiore 0,74 ✓; (b) supera N1 e N2 di almeno 0,03 (0,765 contro 0,710 → +0,055) ✓; (c) 88% delle discese sopra 0,5 ✓; (d) S&P 500 0,768 ✓.

## Cosa si legge, onestamente
- La vecchia «Svolta» dell'Occasione, letta come indice di fase, già valeva 0,77 sull'S&P 500: **i test dei Protocolli 2 e 3 avevano il bersaglio sbagliato** («il minimo regge nelle prossime settimane», «scende ancora del 5%»), troppo rumoroso con pochi episodi. L'indice non era sbagliato come indice di fase.
- Sul solo S&P 500 il nuovo E1 **non batte** il semplice rimbalzo dal minimo (0,78) né la vecchia svolta (0,77). Il guadagno del modello è sull'insieme dei 14 mercati (+0,055 sul rimbalzo) e nella robustezza (ogni mercato sopra 0,5).
- L'indice è soprattutto una **conferma**: riconosce bene che il fondo è alle spalle quando il mercato ha già rimbalzato. Non indica la data del minimo, né di quanto scenderà ancora (questo, nei test precedenti, non si è riusciuto a prevedere).
- Pochi episodi indipendenti sul S&P 500 (18 discese, una parte dei quali legata tra mercati: le crisi globali compaiono in tutte le borse). Intervalli larghi sull'S&P 500 da solo; i 14 mercati non sono indipendenti.
- Il bersaglio usa il minimo noto solo a posteriori: in diretta il minimo del momento può diventare un nuovo minimo più basso.

## Come funziona nell'app
fase_minimo.py: ogni anno il modello (logistica, C=0,1, 15 misure di prezzo) si riaddestra su 14 mercati; punteggio = 1–100 come percentile storico della media fra la probabilità del modello e i cinque segnali semplici. Valori dal 2002. Oggi (24/11/2026): 89, «Discesa in corso, fondo lontano».

## Decisioni
Minimi sostituito dal nuovo indice di fase (peso zero, informativo). L'Indice Occasione (vecchia lettura) resta nella Bussola per le entrate extra. Prova in avanti: il valore giornaliero è nel registro (data/indizi_registro.csv).
