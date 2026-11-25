# Esito: il Super Armor anticipa l'economia? (25 novembre 2026)

Segue PROTOCOLLO_SUPER_ARMOR_ECONOMIA.md (commit 92e0e04, scritto prima dei calcoli). Script scratch/super_armor_economia.py, numeri in scratch/super_armor_economia_esito.json.

## Risposta alla domanda
**No: il Super Armor di prima non anticipa bene l'economia dei prossimi mesi, e l'Indice Armor ancora meno.** L'Indice Armor nasce per misurare il rischio di crollo e volatilità della Borsa (l'economia reale pesa 6%); il Super Armor di prima nasce per il pericolo per la Borsa (sei pilastri Titan) e ha una parte di economia reale. Nei test:
| Punteggio | Correlazione con «economia in peggioramento nei 6 mesi dopo» (verifica 2005–2026) |
|---|---|
| Indice Armor | +0,07 (praticamente nulla) |
| Super Armor di prima | +0,31 [0,10–0,48] |
| **Nuova formula (il peggiore fra finanza ed economia)** | **+0,61 [0,41–0,74]** |
Soglia del caso (95° percentile del migliore su 25): 0,48.

## Cosa è stato misurato
Bersaglio principale Z6: media di tre cambiamenti da oggi a 6 mesi (disoccupazione, posti di lavoro, produzione industriale; dati rivisti), usando per i punteggi solo i dati noti alla data con i ritardi di pubblicazione reali. Secondario R6: inizio di una recessione (NBER) entro 6 mesi. Dal 1992 (storia minima di 5 anni per le misure finanziarie: deviazione dichiarata dal protocollo, che indicava il 1976). Scelta 1992–2004, verifica 2005–2026 (2008 e 2020). 26 alternative.

## Classifica in verifica (correlazione con Z6)
C12 (50% finanza + 50% economia) 0,65 · C17 (prodotto) 0,65 · C14 (30% fin + 70% eco) 0,64 · C23 (logistica annuale) 0,62 · C15 (tutte e 14 uguali) 0,62 · C13 (70/30) 0,61 · C24 (ridge) 0,61 · C20 (peso 3 alla finanza) 0,61 · **C16 (il peggiore dei due) 0,61** · C22 0,60 · C11 (solo economia) 0,56 · C10 (solo finanza) 0,52 · singole misure 0,0–0,53 · Super Armor di prima 0,31 · Indice Armor 0,07.
In scelta (1992–2004) la prima era C16 (0,64), seguita da C18 e C7; per il protocollo la scelta va fatta in scelta, non in verifica: **adottata C16**.
Criteri: (a) 0,61 > soglia 0,48, limite inferiore 0,41 > 0 ✓; (b) supera il Super Armor di prima di 0,30 (≥ 0,05) ✓; (c) prima in scelta ✓; (d) AUC su R6 0,78 [0,57–0,94] con limite inferiore > 0,5 ✓.

## Cosa si legge, onestamente
- La lezione robusta non è «C16 batte tutto»: **tutte le combinazioni di finanza ed economia (C12–C17, C20, C22, C23, C24) valgono 0,60–0,65 e sono tra loro indistinguibili** (differenze dentro l'errore). I pesi esatti contano poco; conta mescolare le due parti. Le due parti da sole valgono meno (finanza 0,52, economia 0,56); le singole misure ancora meno.
- C16 (il peggiore dei due) è stata scelta per regola, perché in scelta era la migliore. La media 50/50 (C12) ha il valore più alto in verifica ma era settima in scelta.
- Anticipo: la correlazione con l'economia a +3 mesi resta 0,55–0,58 e a +9 mesi 0,40–0,45 per le combinazioni: l'orizzonte utile è 3–9 mesi.
- Prima delle ultime tre recessioni (6 mesi prima): C16 valeva 78 (2001), 65 (2008), 64 (2020); il Super Armor di prima 59, 58, 42; l'Indice Armor 58, 61, 40.
- Poche recessioni (2001, 2008, 2020 nella parte comune): intervalli larghi; il bersaglio usa dati rivisti.
- Non prevede i cali di Borsa del giorno dopo e non va letto come tale: per quello c'è il Crollo.

## Formula adottata (Super Armor versione 2)
Due pilastri, ognuno la media di percentili storici (solo passato; alto = peggio):
- **Finanza (veloce), 6 misure con peso uguale (1/6 ciascuna):** curva dei tassi 10 anni−3 mesi invertita; spread del credito (Baa−10 anni); aumento dello spread in 6 mesi; condizioni finanziarie (NFCI); S&P 500 a 12 mesi (invertito); curva 10−2 anni invertita.
- **Economia (lenta), 7 misure con peso uguale (1/7 ciascuna):** richieste di sussidio (rispetto al minimo a 52 settimane); posti di lavoro a 3 mesi (invertito); produzione industriale a 3 mesi (invertita); indice di Chicago (invertito); permessi di costruzione a 6 mesi (invertiti); indicatore di Sahm; fiducia dei consumatori a 6 mesi (invertita).
- **Valore:** il più alto dei due pilastri, portato su 1–100 come percentile storico (non cambia la classifica). Fasce 40/60/80 come l'Indice Armor.
Oggi (24/11/2026): finanza 54, economia 54, Super Armor 47 («Segnali di rallentamento»). Il punto più debole oggi: permessi di costruzione (81), curva dei tassi (76), posti di lavoro (73), produzione (71).

## Decisioni
Il Super Armor mostrato nell'app (Quadro, grafico principale, grafici) usa ora questa formula. Il vecchio Super Armor (SAI dei sei pilastri Titan) resta nei file interni (usato da fasi, convalida delle fasce e modello sistemico) ma non è più mostrato come «Super Armor». Prova in avanti: il valore di ogni giorno è già in data/status_index.json.
