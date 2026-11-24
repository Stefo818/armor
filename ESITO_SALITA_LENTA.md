# Esito: «salita lenta dell'Indice Armor verso 40» (24/11/2026)
Regole: PROTOCOLLO_SALITA_LENTA.md (commit 5d21ed7). Prova su 1990-2020 (non guardato per formare l'ipotesi), blocchi 1990-2004 e 2005-2020. Script `scratch/salita_lenta.py`, numeri in `scratch/salita_lenta_esito.json`.

## Verdetto: NON SUPPORTATO — anzi, il segno è l'opposto
Frequenze di base: indice sopra 60 entro 42 sedute 17,7%; calo −8% in 63 sedute 16,6%; calo −5% in 21 sedute 15,7%.
Dopo una salita lenta della media verso 40 (stato A: 23 episodi; B: 17; C: 8 episodi indipendenti) il rischio è **più basso, non più alto**:
- A: esplosione sopra 60 11% e 12% (base 18%); calo −8%: 14% e 8% (base 17%).
- B: esplosione 3% e 6% (IC90 sotto zero in entrambi i blocchi); calo −8%: 3% nel 1990-2004.
- C: esplosione 0% nel 1990-2004 e 20% nel 2005-2020; calo −8%: 0% e 6%.
Nessuno stato supera la soglia del migliore fra 9 (0,36), nessun IC90 positivo.
Il controllo (stesso livello senza salita) mostra la stessa cosa: sopra 60 entro 42 sedute solo 4-5% dei casi. «Vicino a 40» è la condizione normale (mediana 39, il 42% dei giorni): il livello non dice nulla; e le salite lente verso 40 sono per lo più **riprese dopo una calma profonda**, cioè periodi tranquilli.

## Perché l'impressione del grafico è forte ma non regge
- Ogni esplosione parte da un livello più basso, quindi **prima di ogni picco c'è per forza una salita**: è la lettura al contrario (dato il picco, c'è stata la salita) che il grafico mostra. La domanda utile è l'altra (data la salita, arriva il picco?) e lì la risposta è quasi sempre no.
- Nel 2021-2026 (solo descrittivo, non conta): lo stato A si è acceso 7 volte; il calo −8% in 63 sedute è arrivato in 2 (gen 2022 −10,5%, mar 2025 −13,6%); nelle altre cinque (mar 2021, mar e ott 2023, ago 2024, dic 2025) no. 2 su 7 è in linea con il caso (17-29%). Il 26/10/2026 lo stato A si è riacceso: episodio in corso, non valutabile.
- La memoria visiva privilegia i casi riusciti e dimentica le risalite senza esplosione.

## Cosa si può trarre
1. **La salita lenta verso 40 NON è un segnale di crollo.** Se mai, indica un periodo meno rischioso. Non entra nell'app.
2. L'esplosione dell'indice è un evento rapido che **non si annuncia** con una salita lenta e regolare: quando arriva, parte da livelli bassi e si vede solo dopo.
3. Resta aperta, in un nuovo protocollo, la domanda sulla **velocità** (accelerazione dell'indice a 5-10 sedute, non il livello a 21): non è stata provata ora.
Nell'app non entra nulla; non serve un registro dedicato perché l'Indice Armor è già salvato ogni giorno in `data/titan_storia.csv`.
