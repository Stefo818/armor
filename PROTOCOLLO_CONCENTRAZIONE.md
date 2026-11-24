# Protocollo «Concentrazione del mercato» (bozza del 24/11/2026, da approvare prima di guardare qualsiasi risultato)

## Ipotesi dell'utente
Quando il mercato è troppo sbilanciato su un settore (tecnologia) o su poche aziende (le 10 maggiori) **e** lo sbilanciamento accelera, il mercato si indebolisce e tende a calare. Vale per gli ultimi ~36 anni (dal 1990).

## Cosa si può misurare (dati gratuiti disponibili, storia verificata il 24/11/2026)
Non esistono gratis i pesi storici delle singole aziende o dei settori. Si usano **proxy di prezzo** (rapporti fra indici), tutti con storia lunga:
| Misura | Proxy | Inizio |
|---|---|---|
| Peso della tecnologia (Nasdaq vs resto) | ^NDX / ^GSPC | 1985 |
| Idem, solo tecnologia S&P | XLK / SPY | 1999 |
| Concentrazione sulle grandi (le 100 maggiori vs le 500) | ^OEX / ^GSPC | 1982 |
| Peso delle grandissime (cap-weighted vs pesi uguali) | SPY / RSP; ^GSPC / ^SPXEW | 2003; 2006 |
| Grandi vs medie aziende | ^GSPC / ^MID, ^OEX / ^MID | 1981 |
| Concentrazione dei volumi nei 10 titoli più scambiati | d_quota_volume_top10 (nostro, da 503 titoli) | 2015 |
Il numero esatto «peso % delle 10 maggiori» oggi si può solo stimare: non è dimostrabile all'indietro.

## Indici costruiti
1. **Livello**: posizione percentile (solo passato, finestra espansa) del logaritmo di ogni rapporto; media dei rapporti disponibili in ciascun anno (la lista cambia con la storia disponibile, ma ogni rapporto resta nel suo percentile).
2. **Accelerazione**: variazione a 63 giorni del logaritmo del rapporto e **variazione della variazione** (63 giorni contro i 63 precedenti), entrambe in percentile storico.
3. **Stato combinato**: «sbilanciato e accelera» = livello ≥ 80° percentile **e** accelerazione ≥ 80° percentile; «sbilanciato ma fermo»; «riequilibrio» = livello alto e accelerazione negativa.

## Bersagli (financial-only, stesse finestre ESTERNI delle altre ricerche)
a) calo massimo dell'S&P 500 nei 21 e nei 63 giorni successivi ≥ 5% / ≥ 8% / ≥ 10%; b) rendimento a 63 giorni; c) Nasdaq 100 vs S&P 500 a 63 giorni (rotazione).

## Regole
- Scelta e soglie sul periodo ≤ 2014, verifica su ≥ 2015 (e verifica «a ritroso» su 1985-1999 come prova di stabilità, non per scegliere).
- Soglia del migliore tra N: rimescolamento degli anni (blocchi annuali), 1000 volte, si dichiara N = (numero di rapporti × 3 finestre × 3 bersagli).
- Intervallo di confidenza al 90% con ricampionamento per anno.
- «Dimostrato» solo se il segnale supera la soglia nel campione di scelta **e** nella verifica, nella stessa direzione.
- Si misura anche il valore aggiunto: il segnale aggiunge qualcosa all'Indice crollo e al Terreno fragile? (confronto con e senza, nei giorni in cui l'Indice crollo è basso).
- Episodi indipendenti previsti: pochi (1998-2000, 2007?, 2018, 2021-22, 2024-26). Si dichiarano e si mostrano uno per uno. Sotto i 6 episodi indipendenti l'esito non può essere «dimostrato».
- Esito scritto in ESITO_CONCENTRAZIONE.md anche se negativo. Nell'app solo se «dimostrato»; altrimenti solo scheda informativa con la scritta «non dimostrato».
- Avvertenza dell'ipotesi contraria da verificare: nel 2023-25 la concentrazione è salita molto per anni con il mercato in crescita (segnale alto senza crollo). Un rialzo prolungato con concentrazione alta è un risultato possibile e va riportato.

---
# EMENDAMENTO 1 (24/11/2026, scritto PRIMA di calcolare qualunque risultato)
Su richiesta dell'utente: (1) **il punto non è che il rapporto cresca, ma individuare il punto di rottura**, mettendolo in relazione con tassi e credito; (2) **espandere il periodo** il più indietro possibile. Le regole sotto sostituiscono quelle della bozza dove in conflitto. Nessuna soglia sarà cambiata dopo aver visto i dati.

## Periodo
Dal 1971 (il proxy più lungo della tecnologia, Nasdaq Composite / NYSE Composite) al 2026. Tre blocchi di lettura: **1971-1989** (prima della supremazia tecnologica: serve a vedere se l'idea vale anche quando la tecnologia non dominava), **1990-2014** (scelta), **2015-2026** (verifica). Nessun parametro viene scelto: le soglie sono fisse (80° percentile) e le regole sono qui, quindi la «scelta» non può sovradattare nulla; la verifica resta comunque separata.

## Proxy della concentrazione (log dei rapporti di prezzo)
TEC1 ^IXIC/^NYA (1971), TEC2 ^NDX/^GSPC (1985), TEC3 XLK/SPY (1999), GRA1 ^OEX/^GSPC (1982), GRA2 ^GSPC/^MID (1982), GRA3 SPY/RSP (2003), GRA4 ^GSPC/^SPXEW (2006).
- **Livello** di ogni proxy = punteggio z del log del rapporto rispetto agli ultimi 1260 giorni (5 anni, minimo 750), poi percentile storico espandente (solo passato). Si misura l'**eccesso rispetto al normale degli ultimi anni**, non il rapporto grezzo: un rapporto che sale piano per decenni non è «troppo alto» solo per questo.
- **Accelerazione** = media di due percentili storici: (a) z della variazione a 63 giorni del log del rapporto, (b) variazione della variazione (Δ63 oggi meno Δ63 di 63 giorni fa).
- Composito = media dei proxy disponibili quel giorno (almeno uno).
- **Livello alto** = composito ≥ 0,80; **Accelerazione alta** = composito ≥ 0,80.
- **Inversione della leadership (L)**: livello ≥ 0,80 in almeno un giorno degli ultimi 126, e il composito (z) oggi sotto la sua media a 63 giorni.

## Il punto di rottura: tassi, credito, condizioni finanziarie (tutti con ritardo di pubblicazione)
Quattro inneschi, ognuno «vero» se il suo percentile storico espandente è ≥ 0,80:
- **R1 tassi lunghi in salita**: variazione a 63 giorni del rendimento a 10 anni (dal 1962; ritardo 1 giorno).
- **R2 stretta della banca centrale**: variazione a 126 giorni del tasso sui fondi federali (dal 1954; ritardo 1).
- **C1 credito in tensione**: variazione a 63 giorni dello spread Baa−10 anni (giornaliero dal 1986: `baa10y`); prima del 1986 variazione a 3 mesi dello spread mensile Baa−10 anni (`baa_lungo` − `gs10_m`, ritardo 35 giorni). I percentili si calcolano separatamente sui due pezzi.
- **F1 condizioni finanziarie che si stringono**: variazione a 13 settimane dell'NFCI (dal 1971; ritardo 5 giorni).
**Rottura (RT)** = almeno 2 inneschi su quelli disponibili sono veri.

## Stati da confrontare (7)
S1 = livello alto & accelerazione alta. S2 = S1 & non RT («sbilanciato che accelera, ma tassi e credito calmi»: il caso 2023-25). S3 = S1 & RT («il punto di rottura»). S4 = livello alto & L. S5 = S4 & RT. S6 = livello alto & RT (senza accelerazione). S7 = RT da solo (riferimento: l'effetto dei soli tassi e credito).

## Bersagli (solo crisi finanziarie)
Y(h, soglia) = il minimo dell'S&P 500 nei successivi h giorni di Borsa è almeno `soglia` sotto il prezzo di oggi: (21, 5%), (63, 8%), (63, 12%). Giorni esclusi dal calcolo: le finestre ESTERNI e MISTE_MAX già usate in tutte le ricerche, più (nuove, pre-1986) la finestra dell'embargo petrolifero 17/10/1973 (−5/+60 giorni). Sensibilità: lo stesso con 1973-01 → 1975-06 interamente escluso.
Episodi finanziari di riferimento: la classifica già pubblicata dal 1986 (`classifica_40anni.py`) più, **classificati ora, prima di misurare**: 1976-09-21 (−19%: inflazione e dollaro debole, finanziaria), 1980-11-28 (−27%: stretta di Volcker, tassi al 20%, finanziaria), 1983-10-10 (−14%: rialzo dei tassi e disavanzo, finanziaria). Il 1973-01-11 (−48%) è «mista» (embargo del petrolio + inflazione + stretta + valutazioni): mostrato a parte. Le date si controllano sui prezzi (il massimo reale deve cadere entro 5 giorni, altrimenti si segnala).

## Metriche e regola di «dimostrato»
Per ogni stato e bersaglio: frequenza di Y dentro lo stato, fuori dallo stato, differenza (DR), IC90 della DR con ricampionamento a blocchi di anno (400 giri), in ognuno dei tre blocchi. Soglia del «migliore tra N» (N = 7 stati × 3 bersagli = 21): spostamento circolare dello stato di anni casuali (≥3 anni), 500 volte; si prende il 95° percentile del massimo delle DR sui 21 test. Si riportano gli **episodi indipendenti** (gruppi di giorni accesi separati da almeno 126 giorni) e la **cattura**: quanti episodi finanziari erano segnalati nei 40 giorni fino al massimo.
**Dimostrato** solo se, per almeno 2 bersagli su 3: DR>0 con IC90 sopra zero sia in 1990-2014 sia in 2015-2026, DR di verifica ≥ soglia del migliore-tra-21, e almeno 6 episodi indipendenti in tutta la storia. Altrimenti «indizio» (DR>0 nelle due metà senza il resto) o «non dimostrato». Valore aggiunto: dal 1990, nei giorni in cui l'Indice crollo è basso (<41), lo stato aumenta la frequenza di Y?
Esito in ESITO_CONCENTRAZIONE.md, anche se negativo. Nell'app solo ciò che è «dimostrato»; altrimenti scheda informativa con «non dimostrato».
