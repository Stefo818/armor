# Protocollo: ricerca libera di almeno 1000 tentativi sui segnali prima di correzioni e crolli — 25/11/2026 sera

Scritto prima di calcolare risultati. Libertà piena sui tentativi; regole fisse sulla loro valutazione.

## Bersagli (solo crisi endogene, stesse regole di PROTOCOLLO_ANTICIPO_CORREZIONI.md)
Picchi dell'S&P 500 dal 1990 (massimo in ±20 sedute) seguiti da un calo ≥ 5% entro 120 sedute; esclusi gli shock esterni e le cause miste. **Bersaglio A** = tutte le correzioni endogene (81; 49 moderate, 24 forti, 8 gravi). **Bersaglio B** = quelle con calo ≥ 10% (32: «crisi di mercato e crolli»). Giorno zero = picco p. Finestra di avviso W = p−10…p−2 (almeno 2 sedute di anticipo); W2 = p−3…p−2; W5 = p−6…p−4; W10 = p−10…p−7. Giorni di base = sedute non in [p−40, p+10] di alcuna correzione (anche esterna) né nelle finestre ESTERNI/MISTE_MAX (−5/+60); dal 1992.
**Selezione** = picchi fino al 2007; **verifica** = dal 2008 (mai usata per scegliere).

## I tentativi (generati dal codice; N esatto dichiarato; N ≥ 1000)
1. **Fabbrica generica:** per ~35 serie di base note alla chiusura (S&P 500 prezzo, ampiezza giornaliera, volume, rendimenti; VIX, SKEW; Nasdaq 100, Russell 2000, mid cap, S&P 100, DAX, Nikkei e loro rapporti con l'S&P; 9 settori e rapporti; Baa, alto rendimento, investment grade, stress CISS; curva 10 anni-3 mesi, 10 e 2 anni, dollaro, yen, tasso Fed) si calcolano per finestre n ∈ {2,3,5,10,20,40,60,120,252}: variazione, punteggio z rispetto a media/dev. std. mobili, distanza dal massimo e dal minimo mobili, volatilità delle variazioni, accelerazione (variazione a n meno la stessa n sedute prima), posizione percentile nella finestra. Serie con meno di 100 sedute di storia prima del 1999 escluse (episodi precedenti la serie esclusi dalla misura di quella serie).
2. **Fabbrica specifica S&P:** RSI (2, 3, 5, 14), MACD e sua differenza, Bollinger %B (20, 50), stocastico (5, 14), giorni consecutivi in rialzo/ribasso, giorni sopra/sotto ±1%, ±2 dev. std., gap, posizione di chiusura nel range, ombre, volume su rialzi/ribassi, OBV, autocorrelazione (1-5), asimmetria, curtosi, rapporto di varianza, esponente di Hurst approssimato, entropia dei rendimenti, quota di giorni vicino ai massimi/minimi (varie soglie), conteggio di massimi/minimi nuovi, distanza dalle medie 10/20/50/100/200, incroci fra medie, pendenze, drawdown dal massimo, tempo dal massimo, vicinanza a «livelli tondi» (multipli di 100 punti), mese e giorno della settimana, vigilia di scadenze.
3. **Interazioni:** prodotti e rapporti fra i migliori 30 segnali singoli della selezione di ciascun gruppo (fino a 200 coppie), solo calcolati in selezione.
Ogni misura è provata nei due versi: la direzione è scelta in selezione (verso con AUC più lontana da 0,5) e poi congelata. Statistica di selezione = max(AUC, 1−AUC).

## Misura, soglia contro il caso, verifica
AUC pesata per episodio in W contro i giorni di base (ogni episodio pesa uno). Per la selezione la distribuzione di base usa solo giorni ≤ 2007; per la verifica solo giorni ≥ 2008.
**Soglia «migliore fra N»:** 500 spostamenti circolari casuali (≥ 250 sedute) di tutti i picchi; per ognuno il massimo, fra tutti i tentativi, della statistica di selezione; soglia = 95° percentile di questi massimi (si calcola per bersaglio, includendo tutti gli N tentativi, anche le interazioni).
**Passa** se: statistica di selezione > soglia **e** ≥ 0,60; in verifica AUC (nel verso congelato) ≥ 0,56, limite basso dell'intervallo al 90% (ricampionamento degli episodi di verifica) > 0,5, AUC in W2 > 0,5. Si riportano anticipo tipico (sedute prima di p in cui la misura entra nel 10% più a rischio), quota di episodi con segnale, quota di falsi allarmi sui giorni di base.

## Modelli e combinazioni (altri tentativi, contati in N modelli)
- **Combinazioni dei migliori della selezione:** media delle posizioni percentili (orientate) dei primi K segnali, K ∈ {3, 5, 10, 20, 50}; scelti in selezione, valutati in verifica; p-value di verifica con 500 spostamenti dei picchi di verifica, correzione di Bonferroni (×10 fra combinazioni e modelli).
- **Modelli addestrati in avanti (walk-forward):** regressione logistica regolarizzata (tre livelli) e boosting a alberi poco profondi su tutti i segnali (e sui primi 50 scelti dentro il solo periodo di addestramento), addestrati ogni anno con i soli dati precedenti (da 1992), bersaglio «picco entro 2-10 sedute»; valutati sugli episodi dal 2008. Nessuna messa a punto dopo aver visto i risultati.
Un modello/combinazione «passa» se AUC verifica ≥ 0,60, IC90 basso > 0,5, p-value corretto < 0,05.

## Metriche pratiche per chi passa
Regola di allarme fissata ora: percentile espanso ≥ 90 (e ≥ 80, ≥ 95): episodi con almeno un allarme in W, giorni di allarme nella base (falsi allarmi), precisione (quota di giorni di allarme seguiti da correzione ≥ 5% entro 20 sedute) in verifica.

## Esito
Se nulla passa si scrive. Se qualcosa passa: test in avanti (registrazione giornaliera, nessuna modifica degli indici prima di ≥ 6 mesi) e proposta, non adozione automatica.

## Limiti dichiarati
81 e 32 episodi correlati; migliaia di tentativi → la soglia del caso sale molto: è voluto. Il picco è noto col senno di poi; i segnali sono correlazioni passate.
