# Protocollo «regola di esposizione su VWCE» (scritto il 24/11/2026 ore 16:25, prima di calcolare)

## Domanda (la sola che conta per i soldi)
Usare l'Indice Armor per ridurre l'esposizione quando il terreno è instabile, e tornare pieni quando è calmo, batte il semplice «compra e tieni» **dopo costi e tasse**, o almeno funziona da assicurazione a basso prezzo?

## Mercato e ipotesi realistiche
Prezzi: S&P 500 come sostituto (storia lunga; VWCE parte dal 2019). Dividendi ignorati e liquidità a rendimento zero per entrambe le strategie: penalizza la regola (conservativo). Costi: 0,15% su ogni acquisto o vendita. Tasse italiane: 26% sulle plusvalenze realizzate a ogni vendita (costo medio), senza riporto delle perdite (conservativo); a fine periodo si liquida anche il «compra e tieni» con la stessa imposta. Ordini eseguiti il giorno dopo il segnale (nessun uso del dato del giorno).

## Regole candidate (8, fissate ora)
Indice: `armor_tarato`. Si riduce l'esposizione quando l'indice sale a θ o più, si torna al 100% quando scende sotto θ−5 (isteresi). θ ∈ {55, 60, 65, 70}; esposizione ridotta e ∈ {50%, 0%}. Totale 8 varianti. Confronto: compra e tieni (100% sempre).

## Scelta e verifica
- **Scelta**: 1990-2012, la variante con il miglior rapporto rendimento annuo / perdita massima (dopo costi e tasse, prima della liquidazione finale).
- **Verifica**: 2013-2026-11, una sola variante, nessuna ritaratura. Limite onesto: l'indice stesso è tarato su tutta la storia fino al 2023; solo 2024-2026 è davvero fuori campione, e viene riportato a parte.
- **Rumore**: stesso confronto con il segnale spostato in modo circolare (200 prove, tutte le 8 varianti, si tiene la migliore): la variante scelta deve battere il 95° percentile del migliore-per-caso nel rapporto rendimento/perdita massima.

## Giudizio
- **Dimostrata**: in verifica ricchezza netta finale dopo tassa ≥ compra e tieni, perdita massima più bassa, e supera il rumore.
- **Assicurazione**: perdita massima ridotta di almeno 25% con costo ≤ 0,7% annuo di rendimento, ma ricchezza finale più bassa.
- **Non supportata**: altrimenti.
## App
Dimostrata: schermata «Terreno» con la regola e il confronto. Assicurazione: stessa schermata, etichettata come assicurazione con il costo. Non supportata: solo informativo, nessuna regola.
