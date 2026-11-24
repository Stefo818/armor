# Protocollo «Indice Armor in salita mentre il mercato sale» (scritto il 24/11/2026 ore 16:10, prima di calcolare)

## Osservazione dell'utente
L'Indice Armor cresce anche quando il mercato cresce: quindi anticipa, almeno in parte, i crolli.

## Disegno
Come PROTOCOLLO_SALITA_LENTA.md: l'osservazione nasce dal grafico 2021-2026, quindi si prova su **1990-2020** (blocchi 1990-2004 e 2005-2020, devono reggere entrambi); 2021-2026 solo descrittivo. Indice: `armor_tarato`. Stesse esclusioni di shock esterni e stessa soglia «migliore fra N» (500 spostamenti circolari sul 2005-2020). Limite: la taratura 40/60/80 è fatta sulla storia intera.
Definizioni: «mercato in salita vicino ai massimi» = S&P 500 a meno del 3% dal massimo a 252 sedute e rendimento a 63 sedute ≥ +3%. M10 = media a 10 sedute dell'Indice Armor.

## Stati (fissati ora)
- **D1 divergenza lenta**: mercato in salita vicino ai massimi e M10 più alta di almeno 6 punti rispetto a 42 sedute prima.
- **D2 divergenza veloce**: mercato in salita vicino ai massimi e M10 più alta di almeno 4 punti rispetto a 21 sedute prima.
- **D3 indice alto con mercato forte**: mercato in salita vicino ai massimi e M10 ≥ 45.
- **K (controllo)**: mercato in salita vicino ai massimi e M10 in variazione a 42 sedute inferiore a +2 punti (indice fermo o in calo).

## Bersagli (3)
T2 calo −8% entro 63 sedute; T3 calo −5% entro 21 sedute; T5 calo −10% entro 126 sedute (S&P 500, minimo dal giorno).

## Giudizio
DR con IC90 per anno (400 giri), blocchi 1990-2004 e 2005-2020. **Dimostrato**: per almeno 2 bersagli su 3 IC90 > 0 in entrambi i blocchi, DR 2005-2020 ≥ soglia del migliore fra 9, ≥ 6 episodi indipendenti (gap 126 sedute) e DR > 0 contro il controllo K in entrambi i blocchi. **Indizio**: DR > 0 in entrambi i blocchi su ≥ 2 bersagli. Altrimenti **non supportato**. «Una parte dei crolli»: si conta anche quanti dei picchi endogeni (1990-07, 1997-10, 1998-07, 2000-03, 2007-10, 2010-04, 2011-04, 2018-01, 2022-01) hanno lo stato acceso nelle 126 sedute prima del picco.
## Cosa entra nell'app
Dimostrato: avviso «indice in salita nonostante il mercato». Indizio: riga informativa. Non supportato: nulla.
