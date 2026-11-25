# Protocollo: preavviso del picco da mercato calmo su ~23 borse mondiali — 25/11/2026 notte

Scritto prima dei calcoli. Richiesta: «oltre un miliardo di tentativi, estendere mercati e modelli, scaricare tutti i dati». Onestà preventiva: un miliardo non è eseguibile qui (2 processori; 850000 tentativi hanno richiesto circa un'ora) e non servirebbe: oltre un certo numero più prove alzano solo la soglia del caso. Ciò che può cambiare l'esito è avere **più episodi indipendenti**: per questo si estende ai mercati mondiali già in archivio. Rete: dalla macchina si scaricano solo i dati FRED (nessun indice nuovo oltre a Nikkei, già presente); Yahoo/Stooq sono bloccati da qui. Il budget qui sotto è fissato e non si ripete finché non passa qualcosa.

## Domanda unica
Esiste un segnale, calcolato solo dal prezzo del mercato stesso, che nei **giorni calmi** (volatilità a 60 sedute sotto la propria mediana fino a quel giorno) distingue i giorni che precedono un calo (T1: ≥5% in 20 sedute; T2: ≥8% in 40) dagli altri?

## Mercati (solo chiusure giornaliere, ≥5000 osservazioni, non duplicati degli USA)
S&P 500 (dal 1928), Nikkei (1949), DAX, FTSE, CAC 40, Hang Seng, Canada, IBEX, SMI, AEX, BEL20, ATX, ASX, Bovespa, Messico, Corea, Taiwan, Singapore, Giacarta, Sensex, Shanghai, Tel Aviv, FTSE MIB (se ≥5000 osservazioni). Calo/picco e bersagli calcolati sul mercato stesso. Crisi esterne: per il solo S&P 500 le stesse esclusioni dei protocolli precedenti; per le altre borse non si escludono (dichiarato: il campione estero include anche shock esterni, quindi è un test più duro).

## Divisione dei dati (fissata ora)
Mercati ordinati come sopra: indici pari = **gruppo SEL**, dispari = **gruppo OUT**. Selezione: gruppo SEL, solo date ≤ 2007. Verifica 1 (stessi mercati, nuovo periodo): gruppo SEL ≥ 2008. Verifica 2 (mercati mai usati per scegliere): gruppo OUT, tutte le date. Un segnale è **robusto** solo se passa la selezione E ha AUC ≥ 0,56 nei giorni calmi sia in Verifica 1 sia in Verifica 2 (verso congelato in selezione).

## Segnali (budget fissato ≈ 100000)
Per ogni mercato, con solo il suo prezzo: statistiche (deviazione, deviazione in discesa/salita e rapporto, asimmetria, curtosi, massimo, minimo, distanza da massimo/minimo/media, rendimento, pendenza, curvatura e R² del logaritmo, quota di rialzi, nuovi massimi, autocorrelazione, EWMA, HAR, salti) su finestre 5, 10, 20, 40, 60, 120, 252; varianti (valore, ritardo 5, z a 252, differenza a 20, rapporto alla media a 252); rapporti e differenze fra finestre; poi accoppiamenti casuali (somma, differenza, prodotto) dei percentili di ogni mercato (percentile calcolato sulla storia del mercato stesso fino a quel giorno: espandente, nessun uso del futuro). Totale previsto ≈ 3000 singoli + ≈ 33000 coppie ×3.
Poi fase 2: 30000 insiemi pesati dei 40 migliori in selezione (solo selezione). Modelli: 11 algoritmi × 3 insiemi × 2 bersagli, addestrati sul gruppo SEL ≤ 2007 e provati su Verifica 1 e Verifica 2.

## Giudizio
AUC pooled sui giorni calmi (tutti i mercati del gruppo, righe sovrapposte); soglia «migliore fra N»: 300 spostamenti circolari del bersaglio dentro ciascun mercato, massimo su tutti i segnali, 95° percentile. Si riportano anche p-value con 10000 spostamenti per i migliori (Bonferroni sul numero di candidati). **Esito positivo** solo se un segnale/modello è robusto come sopra e il p-value corretto < 0,05 in entrambe le verifiche. Altrimenti: nessun preavviso trovato anche con 23 mercati.

## Limiti dichiarati
Mercati correlati fra loro (gli episodi globali non sono indipendenti); le chiusure estere possono avere sfasamenti di orario; dati dei listini asiatici più brevi; pochi picchi calmi per mercato.
