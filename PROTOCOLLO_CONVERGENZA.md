# Protocollo «convergenza di segnali deboli» (scritto il 24/11/2026 ore 16:15, prima di calcolare)

## Idea (mia)
Divergenza (indice in salita con mercato alto) vede molti crolli ma sbaglia spesso; velocità (salto rapido) ha segno lieve; il controllo «indice fermo» dimezza i rischi. Nessuno basta da solo. Domanda: **quando più segnali deboli e indipendenti si accendono insieme, la precisione sale?** Se sì, l'app non deve dare allarmi singoli ma un «numero di segnali accesi» con la probabilità storica di calo.

## Disegno
Come i test precedenti: 1990-2020, blocchi 1990-2004 e 2005-2020, esclusioni di shock esterni, episodi indipendenti a 126 sedute, soglia del migliore fra N (spostamenti circolari). Segnali (definizioni già fissate nei protocolli DIVERGENZA e VELOCITA, nessuna nuova soglia): S1 = D1 o D2 (divergenza), S2 = V1 (salto rapido), S3 = indice in M10 ≥ 45 con mercato forte (D3). Conteggio N = S1+S2+S3 nelle ultime 21 sedute. Stati: N≥1, N≥2. Controllo: nessun segnale e indice fermo (K).
Bersagli: −8% in 63, −5% in 21, −10% in 126 sedute. Giudizio: DR con IC90 per anno, entrambi i blocchi; «dimostrato» = IC90>0 in entrambi i blocchi su ≥2 bersagli per N≥2, DR 2005-2020 ≥ soglia, ≥6 episodi; «indizio» = DR>0 in entrambi i blocchi su ≥2 bersagli; altrimenti non supportato. Conta anche se DR cresce con N (monotonia).
