# Esito del protocollo «Terreno» (18 novembre 2026)

Regole: `PROTOCOLLO_TERRENO.md` (scritte e salvate prima di calcolare). Codice delle prove: `scratch/terreno_prova.py`; risultati completi: `scratch/terreno_risultati.json`. Modulo dell'app: `src/armor/terreno.py`.

## Cosa è stato provato
21 variabili in 5 gruppi (credito, famiglie, alternative sicure, flussi e liquidità, imprese), segni e ritardi di pubblicazione fissati prima, standardizzate sul solo passato, riunite in un punteggio unico («Terreno»). 395 fine-mese dal 1994; eventi: calo ≥10% entro 6 mesi (90 eventi su 388 mesi) e calo ≥15% entro 12 mesi (85 su 382). Taratura 1994-2009, conferma 2010-2026 guardata una volta. Controllo con 200 punteggi «sosia» costruiti da rumore.

## Risultato (capacità di distinguere i mesi prima di un calo: 0,50 = moneta, 1 = perfetto)
| | Taratura 1994-2009 | Conferma 2010-2026 (intervallo 90%) | Sosia: 95° percentile in conferma |
|---|---|---|---|
| 6 mesi | 0,83 | **0,49** (0,36; 0,67) | 0,59 |
| 12 mesi | 0,85 | **0,47** (0,30; 0,69) | 0,70 |

Metà della conferma: a 6 mesi 0,59 (2010-17) e 0,37 (2018-26); a 12 mesi 0,82 e 0,28. Il segno non è stabile.

**Verdetto per regola: «non utile».** AUC in conferma ≤ 0,5 a entrambi gli orizzonti. Il Terreno non entra nelle previsioni dell'app (peso zero); resta una scheda informativa in «Segnali di fondo», con la scritta che non prevede.

## Probabilità (guadagno di errore, rispetto alla frequenza storica)
Disegno scelto in taratura: D1 (punteggio unico), +6,4% in media (6 mesi +7,2%, 12 mesi +5,6%, intervalli che includono lo zero). D2 (cinque gruppi separati): −19,8%.
In conferma D1 è peggiore della frequenza storica: −11,4% a 6 mesi (intervallo −17,9; +3,6) e −25,6% a 12 mesi (−33,1; +5,1).
Aggiunto al «mercato» (a 6 mesi il logit di FHS+VIX, a 12 mesi paura e distanza dai massimi): −3,9% a 6 mesi (−11,9; +8,3) e −16,0% a 12 mesi (−22,4; +7,3). Nessun miglioramento.
Nota: nella stessa conferma anche la sola logistica sul mercato perde contro la frequenza (−5,8% e −7,4%): con pochi eventi indipendenti ogni ricalibrazione costa. Per questo il confronto è fatto contro il mercato ricalibrato allo stesso modo.

## Cosa dicono i singoli gruppi (taratura → conferma, 6 mesi / 12 mesi)
- Credito: 0,83 → 0,37 / 0,82 → 0,35. Le singole stretta-prestiti (grandi e piccole imprese), spread BAA e condizioni del credito: da 0,84-0,91 in taratura a 0,30-0,46 in conferma.
- Famiglie: 0,67 → 0,51 / 0,71 → 0,35. Imprese: 0,73 → 0,46 / 0,74 → 0,51.
- **Alternative sicure** (l'idea dei rendimenti alternativi): 0,43 → 0,47 / 0,44 → 0,55. Nessun segnale in nessun periodo.
- **Flussi e liquidità**: 0,32 → 0,51 / 0,35 → 0,52. In taratura il verso era opposto a quello atteso, in conferma nessun segnale.
Tutte le 21 variabili sono nel file dei risultati. Con 21 variabili e 2 orizzonti qualcuna supera 0,5 per fortuna in conferma (prestiti alle imprese a 12 mesi 0,64, carte non pagate 0,57-0,63): non sono state scelte e non vanno lette come scoperte.

## Spiegazione (esplorativa, vista DOPO i risultati: non è una prova)
AUC a 6 mesi per periodo: 1994-2002 0,89; 2003-09 0,77; 2010-14 0,83 (8 eventi); 2015-19 0,40; 2020-26 0,36. Senza il 2020-22 la conferma sale a 0,55.
Lettura: il credito teso e le famiglie in difficoltà hanno preceduto le crisi lente e legate al credito (2000-02, 2008, 2011). I cali più recenti (2015, 2018, 2020, 2022) sono arrivati da shock improvvisi o dai tassi, con banche e famiglie ancora tranquille; il credito si è poi irrigidito dopo i cali, non prima. Questa spiegazione nasce guardando i dati: per poterla usare serve una prova nuova, scritta prima, sui mesi che verranno.

## Cosa resta
- Registro in avanti: ogni mese `data/terreno_registro.csv` salva il Terreno e i cinque gruppi. Tra 12 mesi si potrà confrontare con i cali veri senza toccare nulla.
- Non disponibili gratis con storia: flussi per ETF, acquisti di azioni proprie. Escluse.
- Scostamenti dal protocollo (dettagli tecnici fissati nel codice prima di calcolare, non nel testo): vincolo della logistica C = 0,2, minimo 60 mesi di esiti maturati per cominciare a prevedere; previsione FHS+VIX mensile presa dall'ultima disponibile (massimo 6 giorni prima).
- Limiti: 395 mesi, ma i casi indipendenti sono circa 30; dati macro «come oggi» (revisioni possibili).

## Conclusione
Le pressioni lente su credito e famiglie spiegano bene le crisi lente del passato, ma non sono un segnale utilizzabile per anticipare i cali del tuo ETF: sul periodo non usato per sceglierle sono sparite. Alla domanda «si può migliorare la previsione per questa via?» la risposta dei dati è no, con i dati pubblici gratuiti e per questi eventi. L'app mostra il Terreno come contesto (quanto il bosco è secco) e lo dichiara.
