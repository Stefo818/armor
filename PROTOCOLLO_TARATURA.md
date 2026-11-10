# PROTOCOLLO «TARATURA» — versione 1

Scritto **prima** di vedere i risultati (Patch 60a). Non cambia dopo. Non tocca i protocolli precedenti né i diari firmati.

## Scopo
Verificare se «tarare» le probabilità di calo di A1 e di FHS+VIX (cioè correggerle con quanto è successo davvero in passato) le rende più oneste, in particolare quando la paura (VIX) è alta o bassa. Serve a capire se l'ottimismo di A1 (sottostima del rischio) e l'eccesso di allarme di FHS+VIX a VIX alto si possono correggere senza inventare nulla.

## Metodo (uguale per tutti)
- Previsioni walk-forward 1990-oggi, una data ogni 5 sedute (le stesse della valutazione mensile): A1 e FHS+VIX (peso 0,5 sul VIX).
- Taratura annidata: a ogni data t il correttore si stima solo con coppie (previsione, esito) già note a t (data + orizzonte ≤ t, quindi nessuno sguardo al futuro). Si ristima ogni 10 date. Minimo 150 coppie e 8 eventi.
- Due correttori: **Platt** (regressione logistica sul logit della probabilità: 2 parametri) e **isotonico** (funzione crescente a gradini). Probabilità limitate tra 0,1% e 99,9%.
- **Miscela calibrata (Combinato-Tarato)**: media dei logit di A1 e FHS+VIX, poi Platt. **Media semplice** (senza taratura) come riferimento.
- Esito: calo massimo oltre la soglia entro l'orizzonte (stesse soglie dell'app: 10g 5%; 1m 5% e 10%; 3m 10% e 15%; 6m 10% e 20%). Riferimento «normale»: frequenza storica con soli esiti maturati.
- Misure: Brier Skill Score (BSS) contro il normale, log loss, pendenza di calibrazione (1 = onesta, sotto 1 = troppo estrema), distorsione media (probabilità media meno frequenza reale), AUC. Anche per fasce di VIX alla data della previsione: sotto 18, tra 18 e 25, sopra 25. Sottoperiodi: 2000-2012 e 2013-oggi.

## Regola per usare i numeri tarati (fissata ora)
Una versione tarata sostituisce il genitore nei numeri **mostrati** (decisione della Patch 60b) solo se, sulla soglia principale di ciascun orizzonte (10g 5%, 1m 10%, 3m 10%, 6m 10%):
1. il BSS migliora di almeno 0,005 sia nel 2000-2012 sia nel 2013-oggi, in almeno 3 orizzonti su 4;
2. nessun orizzonte peggiora di oltre 0,005 in uno dei due sottoperiodi;
3. la distorsione media sopra VIX 25 non peggiora in valore assoluto.
Se nessuna versione tarata supera la regola, i numeri restano non tarati e l'app lo scrive.

## Variante V1T1_HAR (in ombra)
Come V1T1 del motore di percorsi, ma con varianza di partenza data dal modello HAR con VIX (HAR-X: previsione a 21 sedute da varianza giornaliera, media a 5 giorni, media a 21 giorni e VIX²). Nell'esperimento VRP (PROTOCOLLO_VRP.md) HAR-X ha battuto il VIX sulla previsione della **varianza** (QLIKE 0,267 contro 0,391), ma sulle **probabilità di calo** non ha mostrato un vantaggio dimostrato. I dati di apertura, massimo e minimo esistono solo dal 2008: la verifica sulle probabilità copre quindi dal 2011, non dal 1994. La variante non può diventare riferimento con questo protocollo: scrive ogni giorno in ombra.

## Classifica dei modelli (Patch 60a)
Voto da 1 a 100 = 50 + 400 × (BSS medio sugli orizzonti principali, media dei due sottoperiodi), limitato a 1-100. 50 = come dire «succede quello che succede di solito». Il margine d'incertezza usa gli intervalli al 90% della valutazione mensile. Il voto «dal vivo» pesa n/(n+400) dove n = previsioni scadute. Nessun modello è promosso dalla classifica.
