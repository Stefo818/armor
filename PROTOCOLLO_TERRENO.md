# Protocollo «Terreno» (scritto il 18 novembre 2026, PRIMA di scaricare i dati nuovi e di calcolare qualunque risultato)

## Domanda
Idea dell'utente: i cali di un ETF mondiale come il VWCE nascono anche da pressioni lente: credito più difficile da ottenere, famiglie e imprese in difficoltà (mutui, carte, risparmi bassi), soldi che vanno verso alternative più sicure e ben pagate (obbligazioni, fondi monetari), liquidità che si ritira. Queste pressioni aiutano a prevedere i cali a **6 e 12 mesi** meglio di quanto già faccia il mercato (prezzi + paura)?

Lezione dei protocolli Titan+ 1-4: a 10 giorni e 1 mese FHS+VIX è praticamente imbattibile; se c'è margine è su orizzonti lunghi. Qui si prova solo lì. Nessuna promessa: se non regge alla conferma, si scrive «non previsivo» e l'app lo dice.

## Dati (tutti pubblici, FRED e serie già nel repository; «come oggi», non «come allora»: limite dichiarato)
Mercato: S&P 500 (chiusure dal 1927). Ritardo di pubblicazione applicato a ogni serie (mesi dopo la data della serie): trimestrali del credito bancario 2; trimestrali di insoluti e debito delle famiglie 5-6; mensili 1-2; giornaliere/settimanali 0.

Cinque gruppi, **segno scelto adesso** (più alto = terreno più fragile; il segno non si cambia dopo):
- **A. Credito** (banche e imprese): sondaggio sulla stretta del credito alle grandi imprese (`sloos`, +, ritardo 2), alle piccole imprese (DRTSCIS, +, 2), sulle carte di credito (DRTSCLCC, +, 2); spread BAA-10 anni (`baa10y`, +, 0); condizioni del credito NFCI (`nfci_credit`, +, 0); crescita a 6 mesi dei prestiti alle imprese (`busloans_g6`, −, 1).
- **B. Famiglie**: insoluti carte (`delinq_cc`, +, 5); insoluti mutui (DRSFRMACBS, +, 5); peso del debito sul reddito (TDSP, +, 6); risparmio sul reddito (PSAVERT, −, 2); variazione a 12 mesi del tasso mutui (MORTGAGE30US, +, 0).
- **C. Alternative sicure e ben pagate**: tasso reale della banca centrale (`real_ff`, +, 1); premio delle azioni sui titoli di Stato (`erp`, −, 1); variazione a 12 mesi del rendimento a 10 anni (`dgs10`, +, 0); curva dei rendimenti 10 anni − 3 mesi (`t10y3m`, −, 0).
- **D. Flussi e liquidità**: debito per comprare titoli, variazione annua (`margin_yoy`, +, 2); moneta M2, variazione annua (`m2_yoy`, −, 2); crescita a 12 mesi dei fondi monetari (`mmf_assets`, +, 1: soldi che cercano rifugio); liquidità netta a 13 settimane (`net_liq_13w`, −, 0).
- **E. Imprese**: insoluti sui prestiti alle imprese (`delinq_biz`, +, 5); perdite su prestiti alle imprese (`chargeoff_biz`, +, 5).
Non disponibili gratis con storia: flussi per ETF, acquisti di azioni proprie. Esclusi, dichiarato.

## Costruzione
Date: ultima seduta di ogni mese, da gennaio 1994 (servono 4 anni di storia per standardizzare). Standardizzazione di ogni variabile sul **solo passato** (media e deviazione espandibili, minimo 48 mesi, tagliata a ±4), con il segno sopra. Punteggio di gruppo = media delle variabili disponibili del gruppo. **Terreno** = media dei gruppi disponibili (almeno 3 su 5). Nessun peso scelto sui dati.

## Eventi (sull'S&P 500, dalla data di valutazione)
- E6: calo massimo ≥ 10% entro 126 sedute.
- E12: calo massimo ≥ 15% entro 252 sedute.
Eventi noti solo a maturazione. Giorni sovrapposti: i casi indipendenti sono pochi (circa 30 anni ÷ 1 anno); tutti gli intervalli usano blocchi di 12 mesi.

## Periodi
Taratura 1994-2009. Conferma 2010-2026, **guardata una sola volta**, solo per il disegno scelto in taratura.

## Disegni in competizione (solo due, dichiarati ora)
- D1: Terreno da solo come punteggio (graduatoria dei mesi), probabilità tramite regressione logistica a due parametri imparata in avanti (solo esiti maturati, minimo 60 mesi, forte vincolo sulla pendenza).
- D2: stessa logistica ma con i cinque punteggi di gruppo separati (vincolo forte).
Si sceglie in taratura quello con il miglior guadagno medio di errore (Brier) rispetto alla frequenza storica; l'altro si riporta comunque.

## Misure e confronti
1. Capacità di distinguere (AUC) del solo punteggio, con intervallo al 90% a blocchi di 12 mesi. Stessa misura per ogni variabile singola (tutte riportate, nessuna scelta a posteriori).
2. Guadagno di errore (Brier) rispetto alla frequenza storica (maturata) dello stesso evento.
3. Guadagno aggiuntivo rispetto al «mercato»: a 6 mesi rispetto a FHS+VIX (previsione già nell'app, mensile); a 12 mesi rispetto a una logistica semplice su paura (VIX) e distanza dai massimi, imparata in avanti. Si misura dando il logit del benchmark + il Terreno alla stessa logistica.
4. **Prova del sosia**: 200 punteggi costruiti con lo stesso metodo ma da serie di puro rumore (passeggiate casuali con la stessa persistenza e lo stesso numero di variabili). Il Terreno deve superare il 95° percentile dei sosia in conferma.
5. Controllo di segno: lo stesso verso (AUC > 0,5) in taratura e conferma e in entrambe le metà della conferma (2010-2017, 2018-2026).

## Etichette e uso nell'app (regola fissata ora)
Per ciascun orizzonte (6 e 12 mesi):
- **Previsivo**: AUC in conferma > 0,60, estremo basso del 90% > 0,5, sopra il 95° dei sosia, stesso segno nelle due metà. Solo allora la probabilità del Terreno può entrare nelle previsioni dell'app (a peso pieno solo se anche il punto 3 è positivo con intervallo sopra zero; altrimenti in ombra).
- **Di contesto**: AUC in conferma > 0,5 ma senza le condizioni sopra. Nell'app: scheda «Terreno» con i quattro gruppi e le frecce, con la scritta «descrive le pressioni, non predice i cali».
- **Non utile**: AUC ≤ 0,5 in conferma. Scheda solo informativa, dichiarato.
Nessuna soglia o segno si cambia dopo aver visto i risultati.

## Limiti da sapere prima
Pochissime crisi vere in 30 anni (2000-02, 2008, 2020, 2022): anche un buon risultato è fragile. I dati macro sono quelli di oggi (revisioni possibili). Un guadagno sotto il 2-3% di errore non è dimostrabile.
