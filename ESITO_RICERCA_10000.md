# Esito: ricerca da oltre 10000 tentativi su discesa e crolli endogeni — 25/11/2026

Protocollo: PROTOCOLLO_RICERCA_10000.md (commit 73fbcd8 + aggiunta 59c26c4, prima dei calcoli). Script: scratch/ricerca_10000.py, supplemento scratch/ricerca_10000_supp.py, copertura scratch/ricerca_10000_cop.py. Dati: scratch/ricerca_10000_esito.json.
**Tentativi: 10856 segnali (3776 singoli + 7080 coppie) + 99 modelli = 10955**, numero fissato in anticipo (non si è continuato fino a «trovare qualcosa»).
Bersagli (solo endogeni, giorni validi dal 1992): T1 calo ≥5% nelle 20 sedute (frequenza 14,9%); T2 calo ≥8% nelle 40 sedute (11,6%); T3 giorni già 2-6% sotto il massimo a 20 sedute, evento = altro calo ≥5% in 20 sedute (20,5%). Selezione ≤2007, verifica ≥2008.

## Segnali singoli e coppie (regola del protocollo)
- Soglia «migliore fra N» (95° percentile del massimo su ~7500 segnali con dati completi): T1 0,793; T2 0,841; T3 0,775. Il migliore reale: T1 0,757; T2 0,826; T3 0,748. **Nessuno la supera: nessun singolo/coppia passa.**
- Il più forte e costante è la **volatilità dei prezzi** (deviazione standard dei rendimenti a 60 giorni dell'S&P 500 e dell'S&P 100; Nasdaq 100): T1 selezione 0,757, verifica 0,675; allarme = top 10% → il calo ≥5% nelle 20 sedute è 2,3-2,7 volte più frequente (lift). Fra i 100 migliori della selezione l'AUC di verifica media è 0,65 (T1), 0,65 (T2), 0,62 (T3); lift mediano 2,3, 2,1, 1,4.
- T3 (discesa in corso): migliori «volatilità a 60 giorni ∧ variazione del credito» (0,748 in selezione, 0,62 in verifica).

## Modelli addestrati in avanti (99; ogni 2 anni da 2008, solo dati precedenti)
Con 300 spostamenti il test del protocollo non poteva essere superato (p minimo 1/301, moltiplicato per la correzione di Bonferroni): errore di progetto, dichiarato. **Supplemento post-hoc con 20000 spostamenti** (stessi modelli e stesse soglie, stessa correzione ×33 per bersaglio):
- T1: 16 modelli su 33 superano (AUC ≥0,60, limite basso al 90% >0,5, lift ≥1,25, p corretto <0,05). Migliori: Bayes ingenuo su 30-100 segnali AUC 0,683, lift 1,93-1,97; alberi estremi su 300 segnali 0,680, lift 2,27; k vicini 0,671, lift 2,00.
- T2: 7 su 33 (Bayes ingenuo 0,684, lift 2,16; foresta casuale 0,673).
- T3 (fase di discesa): 2 su 33 (Bayes ingenuo su 300 segnali 0,650, lift 1,47; k vicini 0,637).
Quindi i modelli addestrati in avanti mostrano un segnale reale ma modesto: AUC 0,65-0,68 sul calo imminente, lift ~2 con l'allarme sul 10% dei giorni (precisione ≈ 30% contro 15% di base per T1).

## Copertura delle correzioni endogene dal 2008 (35 episodi; allarme = 10% più alto delle previsioni del modello nel periodo)
- T1 Bayes 30: allarme in 31% delle correzioni (da 10 sedute prima fino a 5 dopo il picco), 20% dei giorni in allarme; calo residuo mediano al primo allarme −8%.
- T3 Bayes 300 (durante la discesa): 46% delle correzioni, 28% dei giorni; calo residuo −12%.
- Alberi estremi: 14-17% delle correzioni.

## Cosa significa
- Il segnale più forte è «il mercato è già agitato»: la volatilità recente alta separa i giorni prima di nuovi cali da quelli tranquilli, e i modelli aggiungono poco oltre quella. Non è uno stallo sui massimi né un indicatore anticipatore del picco: riconosce che la discesa/agitazione è in corso.
- Non è un allarme da solo: 30% di precisione, mancano più della metà delle correzioni, e molti allarmi sono falsi.
- Oggi: volatilità a 20 sedute al 96° percentile, S&P 500 circa 7% sotto il massimo a 20 sedute (discesa in corso), volatilità a 60 sedute al 80° percentile.

## Test in avanti (partito)
Il registro giornaliero (data/indizi_registro.csv) ora salva: volatilità a 20 e 60 sedute (e loro percentile storico), la coppia volatilità, distanza dal massimo a 20 sedute e un allarme volatilità (percentile ≥90). Nessuna decisione né indice cambia prima di almeno 6 mesi di dati.

## Limiti
Giorni consecutivi correlati (poche decine di episodi indipendenti); soglie del caso severe con 10955 tentativi; il supplemento a 20000 spostamenti è post-hoc (la regola originale era irrealizzabile) ma dichiarato; il taglio dell'allarme per la copertura usa il 90° percentile del periodo di verifica (non quello dell'addestramento), quindi la copertura è leggermente ottimistica; solo dati giornalieri.
