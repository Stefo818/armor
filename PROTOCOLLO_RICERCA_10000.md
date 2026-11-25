# Protocollo: riconoscere la discesa e i crolli endogeni — ricerca da oltre 10000 tentativi — 25/11/2026 sera

Scritto prima di calcolare risultati. Libertà piena sui tentativi, regole fisse sulla loro valutazione. **Il numero di tentativi è fissato in anticipo (≥ 10000, esatto dichiarato dallo script): non si continua «fino a trovare qualcosa»**, perché cercare finché qualcosa passa garantisce un falso positivo. Si riporta quello che esce, anche se è niente.

## Domanda
Individuare, anche con pochi giorni di anticipo, l'inizio e la fase di discesa di una correzione/crollo endogeni, e riconoscere le discese che proseguono (non i rimbalzi). Solo crisi endogene: giorni nelle finestre ESTERNI e MISTE_MAX (−5/+60 sedute, come in tutte le ricerche) esclusi dai bersagli.

## Bersagli (a livello di giorno, S&P 500 dal 1992)
- **T1** (primario): da oggi l'S&P 500 perde ≥ 5% (chiusura minima) nelle 20 sedute successive.
- **T2:** perde ≥ 8% nelle 40 sedute successive (crolli e correzioni forti).
- **T3 (fase di discesa):** giorni in cui la chiusura è 2-6% sotto il massimo a 20 sedute (discesa in corso); etichetta 1 se poi cade di almeno altro 5% in 20 sedute, 0 se rimbalza/si ferma. Riconosce le discese che proseguono.
Il campione di ogni bersaglio = giorni validi (non esterni, con dati completi). Selezione = fino al 2007; verifica = dal 2008 (mai usata per scegliere).

## Tentativi (generati dal codice; N dichiarato)
1. **Fabbrica generica** (1968): 48 serie × (variazioni a 9 finestre, punteggi z, distanze da massimo/minimo, volatilità, posizione stocastica, accelerazione; come in PROTOCOLLO_RICERCA_1000.md).
2. **Fabbrica estesa:** per le stesse serie: z su medie esponenziali (10, 30, 90), correlazione con i rendimenti dell'S&P (20, 60, 120), asimmetria delle variazioni (20, 60), differenze di momentum fra finestre (2-5, 5-20, 10-60, 20-120, 60-252), rapporti di volatilità (5/20, 10/60, 20/120, 60/252), quota di giorni in rialzo (5, 10, 20, 60), serie di giorni consecutivi, drawdown dal massimo storico.
3. **Specifici S&P e di ampiezza:** i 105 della ricerca precedente + RSI su 9 lunghezze, oscillatori, quota di settori sopra/sotto le medie (20, 50, 100, 200), dispersione e correlazione fra settori, numero di indici ai massimi/minimi.
4. **Coppie fissate in anticipo:** 60 «mattoni» (misure rappresentative scelte ora, non dai dati: rendimenti e distanze S&P a più finestre, volatilità, VIX e sue variazioni, SKEW, credito, curva, dollaro, medie aziende e piccole aziende rispetto all'S&P, settori difensivi/ciclici, ampiezza), trasformati in posizione percentile; per ogni coppia (1770): minimo (E), massimo (O) e prodotto (P) delle posizioni, con il verso fissato ora (alto = rischio per ogni mattone). N di coppie = 5310.
5. **Modelli addestrati in avanti** (rifatti ogni 2 anni da 2008, solo dati precedenti meno 130 sedute): algoritmi = regressione logistica L2 (due livelli), L1, analisi discriminante lineare, Bayes ingenuo, k vicini (50), foresta casuale (profondità 5), alberi estremi, boosting a alberi (profondità 2, 3, 4); insiemi di segnali = i primi 30, 100, 300 per AUC nel solo addestramento; per ciascun bersaglio. ≈ 90 modelli.
Ogni segnale singolo/coppia è provato nei due versi: il verso si sceglie in selezione e si congela.

## Misura e convalida
AUC sul giorno (probabilità che un giorno con l'evento davanti abbia il segnale più alto di un giorno senza). Statistica di selezione = max(AUC, 1−AUC) sul periodo ≤ 2007. **Soglia «migliore fra N»:** 300 spostamenti circolari casuali (≥ 250 sedute) del bersaglio e della sua maschera dei giorni validi rispetto ai segnali; per ognuno il massimo su tutti gli N tentativi; soglia = 95° percentile dei massimi (per bersaglio, N completo).
**Passa** se: statistica di selezione > soglia **e** ≥ 0,58; in verifica (verso congelato) AUC ≥ 0,56, limite basso al 90% > 0,5 (ricampionamento a blocchi trimestrali, 1000 volte), «lift» ≥ 1,25 con allarme = segnale sopra il 90° percentile dei giorni di selezione (soglia congelata): lift = frequenza dell'evento nei giorni di allarme / frequenza nei giorni validi.
**Modelli:** AUC pooled 2008-2026 ≥ 0,60, limite basso > 0,5, lift ≥ 1,25 con soglia = 90° percentile del punteggio nell'addestramento, p-value (300 spostamenti del bersaglio) con correzione di Bonferroni per il numero di modelli < 0,05.
Per ogni «passa»: copertura di episodi (nelle 81 correzioni endogene, quota con almeno un allarme nelle sedute p+1…p+5 e quota di calo residuo ancora davanti al primo allarme), giorni di allarme, falsi allarmi.

## Esito
Se qualcosa passa: si registra ogni giorno il segnale (test in avanti, nessuna modifica degli indici prima di ≥ 6 mesi). Altrimenti si dichiara: nessun segnale utile con questi dati.

## Limiti dichiarati
Cali correlati, pochi episodi indipendenti (~81 correzioni endogene); 10000+ tentativi → soglia severa, voluta; segnali basati su dati giornalieri; nessuna informazione intraday/notizie/posizionamento.

## Aggiunta (25/11/2026, prima di eseguire): conteggio dei tentativi
Per raggiungere ≥ 10000 tentativi come dichiarato: (a) la fabbrica estesa comprende anche, per ogni serie, le variazioni a 5 e 20 sedute ritardate di 1, 2, 3, 5 sedute, il massimo mobile a 20 sedute delle variazioni a 5 sedute (e minimo), la variazione a 20 della volatilità a 20 e lo z a 252 della volatilità a 20; (b) per ogni coppia di mattoni si prova anche la differenza delle posizioni (1770 in più). Resto invariato.
