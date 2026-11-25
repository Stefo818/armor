# Protocollo: ricerca estesa (oltre 100000 + oltre 100000 tentativi), con dati dal 1928 e letteratura — 25/11/2026 notte

Scritto prima di calcolare risultati. Richiesta dell'utente: «oltre 100000 tentativi (accoppiamenti, range, sfasamenti, algoritmi, modelli, pesi, valori diversi), consultando le fonti più accreditate; poi altri 100000 tentativi per valorizzare i più promettenti».

## Principi (dichiarati prima)
1. Il numero di tentativi è fissato (fase 1 ≥ 100000, fase 2 ≥ 100000): **non si continua finché qualcosa passa**. Più tentativi alzano la soglia del caso: non creano informazione. Si riporta l'esito qualunque sia.
2. Il periodo 2008-oggi è già stato guardato in studi precedenti (è «semi-pulito»). **Dato davvero mai usato = S&P 500 dal 1928 al 1989** (tutti gli studi precedenti partono dal 1990): serve come verifica pulita per i segnali calcolabili con prezzi e dati macro lunghi. I segnali che usano dati dal 1990 in poi (VIX, settori, credito giornaliero…) si verificano solo sul 2008-oggi e restano «semi-puliti».
3. I tentativi della fase 2 si scelgono **solo con la selezione**; mai in base alla verifica.

## Letteratura consultata (da cui nascono le famiglie)
Kritzman et al. (absorption ratio, indice di turbolenza di Mahalanobis); Greenwood, Shleifer, You, «Bubbles for Fama» (forti rialzi, volatilità, percorso del prezzo predicono crolli, non i rendimenti); Sornette e coautori (LPPLS: crescita più veloce dell'esponenziale, indicatore di confidenza); Haase e Neuenkirch (recessioni di Borsa, Markov-switching, 92 variabili); Roberts, Bank of Canada 2017 (valutazione e crolli); studi sui mercati ribassisti (spread dei rendimenti, curva, inflazione); letteratura GARCH/HAR sulla volatilità (i forti cali recenti predicono la volatilità, non viceversa). Famiglie corrispondenti: volatilità e regimi (GARCH-lite, asimmetria), curvatura del logaritmo del prezzo (proxy LPPLS), rialzi lunghi (2-3 anni), turbolenza e assorbimento su indici internazionali, valutazione (CAPE), spread e curva (dal 1919/1953), inflazione, momentum.

## Bersagli e campioni (come in PROTOCOLLO_RICERCA_10000.md: T1 calo ≥5% in 20 sedute; T2 ≥8% in 40; T3 fase di discesa che prosegue)
Solo endogeni. Esclusi: dal 1990 le finestre ESTERNI/MISTE_MAX; **prima del 1990 (dichiarate ora):** guerra 1939-09-01 → 1945-09-02 interamente; poi 1950-06-25, 1956-10-29, 1962-10-22, 1963-11-22, 1973-10-17, 1979-11-04, ciascuna da −5 a +60 sedute. Periodi: **VECCHIO** = 1932-1989 (verifica pulita, solo gruppo P), **SELEZIONE** = 1992-2007, **VERIFICA** = 2008-oggi.

## Fase 1: tentativi
**Gruppo P (solo prezzi dell'S&P 500 e macro lunghi, dal 1928):** statistiche (media, deviazione standard, deviazione in discesa e in salita e loro rapporto, asimmetria, curtosi, massimo, minimo, quantili 5 e 95, somma dei valori assoluti, quota di rialzi, quota sotto −1% e sopra +1%, distanza da massimo, minimo e media, pendenza e **curvatura** (proxy LPPLS) e R² del trend del logaritmo del prezzo, autocorrelazione, ampiezza, nuovi massimi, rendimento) su 17 finestre (2…504 sedute); trasformazioni: ritardi 1, 2, 3, 5, 10, 20; z a 252 e 1008; differenze a 5 e 20; rapporto alla media a 252; relazioni fra finestre (rapporto e differenza di 14 statistiche su tutte le 136 coppie di finestre); macro lunghi (spread Baa-Aaa, Baa, 10 anni, curva, CAPE, inflazione, produzione industriale, ecc., ritardati di un mese): livello, variazioni a 1, 3, 6, 12 mesi, z a 60 mesi; **accoppiamenti casuali** (45000 coppie di segnali, somma, differenza e prodotto degli z: 135000). Totale previsto ≈ 144000.
**Gruppo A (dati dal 1990):** i 10856 segnali della ricerca precedente, 8 misure di turbolenza e assorbimento su 6 indici internazionali (finestre 60, 120, 250), più 30000 coppie casuali dei segnali singoli (somma, differenza, prodotto: 90000). Totale ≈ 101000.
**Modelli in avanti:** algoritmi (regressione logistica L2/L1, analisi discriminante, Bayes ingenuo, k vicini, foresta, alberi estremi, boosting) × insiemi (primi 30, 100, 300 per AUC) × 3 bersagli = 99 modelli: (i) **addestrati sul solo VECCHIO (1932-1989) e provati su 1992-oggi** (gruppo P); (ii) walk-forward come in PROTOCOLLO_RICERCA_10000.md (gruppo A).

## Misura e regole di giudizio
AUC sul giorno; statistica di selezione max(AUC, 1−AUC) su SELEZIONE; soglia «migliore fra N»: 300 spostamenti circolari del bersaglio sul campione di selezione, massimo su tutti i segnali del gruppo; soglia = 95° percentile. Un segnale passa la selezione se > soglia e ≥ 0,58. **Segnale robusto** = passa selezione **e** (verso congelato) VERIFICA AUC ≥ 0,56 con lift ≥ 1,25 (allarme = 90° percentile della selezione) **e**, per il gruppo P, VECCHIO AUC ≥ 0,55 con lift ≥ 1,15. Modelli: AUC ≥ 0,60 sul periodo non visto, lift ≥ 1,25, p-value con 20000 spostamenti, Bonferroni ×33 per bersaglio < 0,05.

## Fase 2: valorizzare i più promettenti (≥ 100000 tentativi, scelti solo in selezione)
Per ciascun bersaglio e ciascun gruppo: si prendono i 40 migliori segnali della selezione (verso congelato) e si provano **100000 insiemi pesati casuali** (sottoinsiemi di 2-12 segnali, pesi di Dirichlet) più 1500 regole a soglia (40 segnali × 50 soglie di percentile 50-99). Si scelgono i 10 migliori in selezione e si valutano su VERIFICA e (P) VECCHIO: AUC, limite basso al 90% (ricampionamento a blocchi trimestrali), lift, p-value con 20000 spostamenti con Bonferroni ×10. «Promettente confermato» solo se AUC ≥ 0,60 e lift ≥ 1,25 su tutti i periodi non usati per la scelta.

## Copertura e test in avanti
Per ogni segnale robusto: quota di correzioni endogene (dal 2008) con allarme da 10 sedute prima fino a 5 dopo il picco, giorni in allarme, precisione. Segnali registrati nel registro giornaliero per ≥ 6 mesi prima di ogni modifica.

## Limiti dichiarati
Pochi episodi indipendenti; dati giornalieri di sola chiusura prima del 1990; classificazione esterno/endogeno prima del 1990 grossolana; esiti senza conferma pulita restano ipotesi.
