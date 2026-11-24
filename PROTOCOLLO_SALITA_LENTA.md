# Protocollo «salita lenta dell'Indice Armor verso 40» (scritto il 24/11/2026 ore 16:05, prima di calcolare)

## Osservazione dell'utente
Negli ultimi 5 anni, quando la media dell'Indice Armor cresce piano fino a lambire 40, poi in poche settimane esplode e arriva il calo. Si può trarre qualcosa?

## Disegno (regola d'oro: l'osservazione nasce dal 2021-2026, quindi quei dati NON valgono come prova)
Si prova su **1990-2020**, mai guardato per questa ipotesi, in due blocchi: **1990-2004** e **2005-2020** (devono reggere entrambi). Il 2021-2026 resta solo descrittivo (elenco degli episodi, non conta).
Indice: `armor_tarato` di data/titan_storia.csv (il numero mostrato nell'app). Limite dichiarato: la taratura delle soglie 40/60/80 è stata fatta sulla storia intera, quindi è in parte «dentro il campione»; il test misura la forma del movimento, non la bontà delle soglie.
Fatto importante già noto: la mediana dell'indice è 39 e il 42% dei giorni ha la media a 21 sedute fra 36 e 44. **«Vicino a 40» è la condizione normale**: conta la salita, non il livello. Per questo c'è uno stato di controllo.

## Stati (fissati ora; M21 = media a 21 sedute, M63 = media a 63 sedute dell'indice)
- **A**: M21 fra 37 e 45 e M21 più alta di almeno 4 punti rispetto a 42 sedute prima.
- **B**: M63 fra 37 e 45 e M63 più alta di almeno 3 punti rispetto a 63 sedute prima.
- **C**: come A, e inoltre M21 è stata ≤ 33 in almeno un giorno delle ultime 126 sedute (parte da una calma profonda).
- **K (controllo)**: M21 fra 37 e 45 con variazione a 42 sedute inferiore a +1 punto (stesso livello, senza salita).

## Bersagli (3) e finestre
T1 «esplosione»: l'indice supera 60 almeno un giorno nelle 42 sedute successive. T2: l'S&P 500 scende di almeno 8% entro 63 sedute. T3: l'S&P 500 scende di almeno 5% entro 21 sedute. Escluse le finestre di shock esterni e il 1973 come nei protocolli precedenti.

## Misure e giudizio
DR = P(bersaglio | stato) − P(bersaglio | non stato), IC90 per anno (400 giri). Soglia «migliore fra N» (N = 3 stati × 3 bersagli = 9) con 500 spostamenti circolari sul blocco 2005-2020.
**Dimostrato**: per almeno 2 bersagli su 3, IC90 > 0 in entrambi i blocchi, DR 2005-2020 ≥ soglia, ≥ 6 episodi indipendenti (accensioni a più di 126 sedute l'una dall'altra) nel 1990-2020, e DR rispetto al controllo K > 0 in entrambi i blocchi (cioè conta la salita, non il livello). **Indizio**: DR > 0 in entrambi i blocchi su ≥ 2 bersagli. Altrimenti **non supportato**.
Descrittivo: tempo tipico fra l'accensione e il superamento di 60; episodi del 2021-2026 e cosa è successo; stato di oggi.

## Cosa entra nell'app
Dimostrato: avviso «preallarme: salita lenta» con probabilità storica. Indizio: riga informativa. Non supportato: nulla (solo registro giornaliero `data/salita_lenta_registro.csv`, peso zero).
