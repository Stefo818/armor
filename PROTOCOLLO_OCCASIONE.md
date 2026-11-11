# Protocollo «Occasione, fasi e salute» (scritto l'11 novembre 2026, PRIMA di vedere i risultati)

Scopo: aiutare chi fa un piano di accumulo su VWCE a decidere **quando fare le entrate extra**. Non è una previsione certa e non è un consiglio.
Le regole qui sotto sono fissate ora. I numeri (soglie, pesi) non si cambiano dopo aver visto i risultati: se una parte non supera la prova, si dichiara e si toglie.

## 1. Indice Occasione (da 0 a 100)

Due parti. Ogni voce vale da 0 a 100 (lineare tra i due estremi, tagliata fuori). Ogni voce usa solo dati già noti quel giorno.

**Panico** = media delle voci disponibili (ne servono almeno 3):
| Voce | 0 punti | 100 punti | Dati dal |
|---|---|---|---|
| Caduta: S&P 500 sotto il massimo dell'ultimo anno (252 sedute) | −5% | −25% | 1928 |
| Paura: indice della paura (VIX) | 20 | 45 | 1990 |
| Paura a breve più alta di quella a tre mesi (VIX diviso VIX a 3 mesi) | 0,95 | 1,15 | 2006 |
| Credito: aumento in 63 sedute della distanza tra tassi delle aziende (Baa) e titoli di Stato a 10 anni | +0,10 punti | +1,00 punti | 1986 |
| Sotto la media: S&P 500 sotto la sua media di 200 sedute | 0% | −15% | 1928 |

**Svolta** = media delle voci disponibili (ne servono almeno 3):
| Voce | 0 punti | 100 punti | Dati dal |
|---|---|---|---|
| Paura che rientra: VIX sceso dal suo massimo di 63 sedute (vale solo se quel massimo è almeno 28, altrimenti 0) | 0% | −35% | 1990 |
| Curva della paura tornata normale (VIX diviso VIX a 3 mesi) | 1,05 | 0,95 | 2006 |
| Credito che smette di peggiorare: distanza Baa − 10 anni sotto la sua media di 21 sedute | 0 punti | 0,15 punti | 1986 |
| Prezzo che risale dal minimo di 63 sedute | +3% | +12% | 1928 |
| Ampiezza: quota dei 9 settori sopra la propria media di 20 sedute | 30% | 90% | 1999 |

**Panico recente** = il valore più alto del Panico nelle ultime 63 sedute.
**Indice Occasione** = il più basso tra Panico recente e Svolta (servono tutti e due).

Stati:
- **Nessun panico**: Panico recente sotto 30.
- **Coltello che cade**: Panico di oggi almeno 40 e Svolta sotto 40 (si scende ancora: aspettare).
- **Occasione**: Indice Occasione almeno 50. **Occasione forte**: almeno 70.
- **In osservazione**: tutti gli altri casi.

Versione lunga (1928-1989, senza VIX): al posto del VIX si usa la volatilità reale di 21 sedute annualizzata (Paura: 0 a 15%, 100 a 45%; «rientra»: vale se il massimo di 63 sedute è almeno 25%). Serve solo come prova in più, con almeno 2 voci per parte.

### Prove (S&P 500, 1990-2026; due metà: 1990-2007 e 2008-2026)
- **P1 Rendimenti dopo il segnale.** Giorni con Occasione ≥ 50 contro tutti i giorni: rendimento a 6 e 12 mesi (medio, mediano, quota positiva). Superata se in entrambe le metà il rendimento mediano a 12 mesi supera quello di tutti i giorni di almeno 5 punti e la quota positiva non è più bassa.
- **P2 La Svolta serve?** Confronto con «comprare il panico» (Panico ≥ 50 senza Svolta): ulteriore discesa massima nelle 63 sedute dopo. Superata se con Occasione ≥ 50 la discesa media è più piccola di almeno un terzo. Se fallisce, la Svolta si toglie.
- **P3 Vicinanza ai minimi.** Per ogni discesa di almeno 15% dal massimo dell'anno: il primo giorno con Occasione ≥ 50. Superata se in almeno 2 episodi su 3 il segnale arriva entro 30 sedute dal minimo e a non più del 10% sopra il prezzo minimo, e se al massimo 1 episodio su 3 ha un segnale seguito da un'altra discesa oltre il 10%.
- **P4 Falsi allarmi.** Numero di segnali fuori dagli episodi di discesa ≥ 10% (si contano gli episodi, non i giorni; due segnali sono distinti se separati da almeno 126 sedute).

## 2. Entrate extra: quando conviene

Rendimento totale (prezzo + dividendi). I soldi fermi rendono il tasso dei titoli di Stato a 3 mesi.
**Prova A, soldi che arrivano in un giorno qualsiasi** (un arrivo al mese, risultato dopo 5 anni):
- «Subito»: si investe il giorno stesso.
- «In 12 rate»: un dodicesimo al mese.
- «Aspetto l'occasione»: si investe al primo giorno con Occasione ≥ 50; se non arriva entro 12 mesi, si investe comunque.
- «Aspetto solo se il rischio è alto»: se quel giorno l'Indice Armor è 40 o più si aspetta l'Occasione (al massimo 6 mesi); altrimenti si investe subito.
**Prova B, riserva mensile** (ogni mese una quota extra fissa):
- «Subito» ogni mese.
- «Scaglioni»: la riserva si investe per 1/3 al primo −10% dal massimo dell'anno, metà del resto al −20%, tutto al −30%; le soglie si riattivano a un nuovo massimo.
- «Scaglioni con svolta»: come sopra, ma ogni scaglione parte al primo giorno con Svolta ≥ 50 dopo aver toccato la soglia.
- «Occasione»: tutta la riserva al primo giorno con Occasione ≥ 50 (si riattiva quando scende sotto 30).
Superata solo se una regola batte «Subito» sul periodo intero **e** in almeno metà delle finestre di 15 anni. Se nessuna la supera, l'app lo scrive chiaramente.

## 3. Fasi e fasce di rendimento per orizzonte

Orizzonti: 1 settimana (5 sedute), 1 mese (21), 3 mesi (63), 6 mesi (126), 12 mesi (252).
Metodo «situazioni simili»: lo stato di oggi è descritto da 6 numeri, ognuno espresso come posizione (da 0 a 1) nella propria storia fino a quel giorno: VIX, distanza dalla media di 200 sedute, caduta dal massimo dell'anno, rendimento di 21 sedute, Indice Armor, Super Armor.
Per ogni giorno si cercano nel passato (solo giorni il cui esito era già noto) i giorni più simili: il 5% più vicino, almeno 150. Dai loro rendimenti successivi: fascia 10°-90° percentile, valore centrale, probabilità di rialzo, probabilità di perdere più del 5% e di guadagnare più del 5%.
Confronti: (a) fascia storica semplice (tutti i giorni passati); (b) situazioni simili solo per VIX.

Prove fuori campione (dal 2000, un giorno ogni 5; due metà: 2000-2012 e 2013-2026):
- **F1 Copertura**: la fascia 10°-90° deve contenere il risultato tra il 72% e l'88% delle volte.
- **F2 Precisione della fascia**: errore sui percentili 10, 50, 90 più basso della fascia storica semplice in entrambe le metà.
- **F3 Direzione**: quando la probabilità di rialzo è almeno 70%, la frequenza reale; quando è al massimo 45%, la frequenza reale. Vale solo se la differenza con la frequenza di base ha lo stesso segno in entrambe le metà.

Etichette di fase (per orizzonte), fissate ora:
- **Rialzo probabile**: probabilità di rialzo ≥ 65% e valore centrale sopra il valore centrale storico.
- **Ribasso probabile**: probabilità di rialzo ≤ 45%.
- **Stabile**: fascia più stretta della fascia storica e nessuno dei due casi sopra.
- **Agitato**: gli altri casi.
- **Minimo in formazione**: Indice Occasione ≥ 50 (si mostra accanto alla fase).
Le etichette si mostrano solo per gli orizzonti in cui F3 è superata; altrimenti si mostra solo la fascia.

## 4. Stato di salute

- **Salute del mercato** (dall'Indice Armor): In salute sotto 35, Neutro 35-40, Rischio 40-45, Pericolo da 45.
- **Salute di economia e finanza** (dal Super Armor): In salute sotto 35, Neutro 35-45, Rischio 45-55, Pericolo da 55.
Accanto si mostra la posizione nella storia («più alto del X% dei giorni dal 1990»).
Prova: frequenza di una discesa ≥ 10% nei 3 mesi dopo, per fascia, separata in 1995-2010 e 2011-2026. Superata se la frequenza cresce da una fascia alla successiva in entrambe le metà (è ammessa una sola inversione).

## 5. I sei pilastri
Controllo di ogni pilastro da solo, per orizzonte (capacità di distinguere i periodi con discesa ≥ 10%, nelle due metà). Nessuna modifica al motore Titan v47 senza una prova scritta in anticipo: i cambi proposti girano prima in parallelo.

## Esito delle prove (11 novembre 2026, dopo aver fissato le regole sopra)
- **P1 non superata.** L'indice ha funzionato in 1950-1967, 1968-1989 e 2008-2026; non ha funzionato in 1928-1949 e 1990-2007 (ribassi lunghi: 1929-1932, 2000-2002).
- **P2 non superata di poco** (discesa media dopo il segnale −6,4% contro −8,8% del solo panico: meno di un terzo). La Svolta resta perché evita gli ingressi peggiori dal 2008, ma è dichiarato.
- **P3 non superata**: 3 episodi su 8 con segnale vicino al minimo secondo la regola stretta (5 su 8 con segnale dopo il minimo e nessuna altra discesa); nel 2000-2002 e nel 2007-2009 il primo segnale è arrivato molto prima del minimo.
- **P4**: nessun segnale fuori da discese di almeno il 12%.
- **Entrate extra (prova A)**: nessuna regola di attesa batte «subito». L'app lo scrive.
- **Un filtro provato e scartato**: «lavoro in peggioramento» (richieste di sussidio) separava bene i segnali sbagliati nel 1990-2026 ma non nel 1968-1989, mai guardato prima: non si usa.
- **F1-F2**: la fascia per «paura simile» regge a 1 settimana, 1 mese, 6 e 12 mesi (di poco); a 3 mesi è pari alla storia. Le sei misure insieme sono peggio della sola paura: si usa solo la paura.
- **F3 non superata**: nessuna capacità di prevedere la direzione. Le etichette «rialzo probabile» e «ribasso probabile» non si mostrano; si mostra la fase di tendenza di oggi (regola dei 200 giorni), che in tutte le epoche distingue il rischio a 1-3 mesi.
- **Salute superata**: la frequenza di discese cresce da uno stato al successivo in entrambe le metà (una sola inversione per il Super Armor nel 2011-2026).
Conclusione: l'Indice Occasione si mostra come aiuto a riconoscere i minimi dei cali veloci, con la pagella completa e l'avviso sui ribassi lunghi. Non è una regola per tenere soldi fermi.
