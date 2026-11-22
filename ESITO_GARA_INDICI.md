# Esito — Gara fra gli indici
Regole: `PROTOCOLLO_GARA_INDICI.md`, pubblicato prima dei calcoli (commit d399b13).
81 candidati: 3 indici (Indice Armor tarato, Super Armor, Indice crollo) × 9 modi di misurarli (livello,
medie a 5/21/63/126 sedute, sedute sopra 60 nelle ultime 5/21/63/126) × 3 orizzonti.
Scelta sul 1990-2014, verifica sul 2015-2026, sole crisi finanziarie.

## 1. Quanto vale «la migliore su 81» per puro caso
Mescolando i bersagli ad anni interi e rifacendo tutte le 81 prove, la migliore raggiunge **0,6805** in
mediana e **0,7460** al 95° percentile. Questa è la soglia da battere: sotto, un candidato non si
distingue da quello che il caso produce quando si sceglie il meglio di ottantuno.

## 2. Una settimana (calo del 3% entro 5 sedute, base 6,7%) — **PROMOSSO**
| candidato | scelta 1990-2014 | verifica 2015-2026 |
|---|---|---|
| **Indice crollo · media 5 sedute** | 0,7493 | **0,7493** |
| Indice crollo · livello di oggi | 0,7449 | 0,7483 |
| Indice crollo · media 21 sedute | 0,7437 | 0,7021 |
| Indice crollo · sedute sopra 60 su 63 | 0,7312 | 0,6437 |
| Indice crollo · media 63 sedute | 0,7263 | 0,6779 |

Vincitore: **Indice crollo, media delle ultime 5 sedute**. Verifica 0,7493, intervallo al 90%
[0,6505 – 0,8014]. Nel quinto più alto il calo è arrivato nel **18,0%** dei casi contro il **6,7%** di
base. Supera G1, G2 e G3 — ma G2 di poco: 0,7493 contro la soglia del caso di 0,7460. È un indizio
stretto. Le prime otto posizioni sono **tutte** dell'Indice crollo: su questo orizzonte è nettamente il
migliore dei tre.

## 3. Un mese (calo del 5% entro 21 sedute, base 11,0%) — **non promosso**
| candidato | scelta | verifica |
|---|---|---|
| Indice Armor · media 63 sedute | 0,7377 | **0,5443** |
| Indice crollo · sedute sopra 60 su 63 | 0,7350 | 0,5625 |
| Indice Armor · media 126 sedute | 0,7348 | 0,5921 |
| Indice crollo · media 21 sedute | 0,7335 | 0,6691 |

Il vincitore della scelta **crolla da 0,7377 a 0,5443** nella verifica: quasi il caso. Non promosso.
Nota importante: l'Indice crollo a 21 sedute regge meglio (0,6691), ma non era il vincitore della scelta
e **non lo si può ripescare dopo**: sarebbe esattamente il trucco contro cui serve il protocollo.

## 4. Tre mesi (calo dell'8% entro 63 sedute, base 13,9%) — **non promosso**
| candidato | scelta | verifica |
|---|---|---|
| Indice Armor · media 126 sedute | **0,8123** | **0,5404** |
| Indice Armor · media 63 sedute | 0,8072 | 0,5206 |
| Indice crollo · sedute sopra 60 su 126 | 0,7941 | 0,4918 |

Da 0,8123 a 0,5404. È la dimostrazione più chiara di tutta questa ricerca: **il candidato che sembrava
migliore di tutti è quello che fuori campione vale di meno.** Le medie lunghe si adattano agli episodi
passati e non trasferiscono.

## 5. La tensione aiuta? No
Le misure di persistenza («quante sedute sopra 60») non vincono mai e perdono molto nella verifica. Il
miglior modo di leggere un indice resta il più semplice: il livello di oggi o la media di cinque sedute.

## 6. La domanda diretta dell'utente: sopra 60 per quanto tempo?
Misurato su tutte le crisi finanziarie dal 1990, per «almeno metà delle sedute della finestra sopra 60».
Calo dell'8% entro tre mesi (base 16,8%):

| indice | sopra 60 per | giorni | episodi | calo poi | volte la base |
|---|---|---|---|---|---|
| Super Armor | una settimana | 515 | 17 | **54,8%** | 3,3× |
| Super Armor | un mese | 501 | 13 | 53,9% | 3,2× |
| Indice Armor | sei mesi | 408 | **5** | 64,2% | 3,8× |
| Indice Armor | un mese | 510 | 11 | 47,3% | 2,8× |
| Indice Armor | una settimana | 514 | 26 | 44,7% | 2,7× |
| Indice crollo | sei mesi | 1.412 | 11 | 43,3% | 2,6× |
| Indice crollo | una settimana | 1.524 | **68** | 39,2% | 2,3× |

Calo del 5% entro un mese (base 15,4%): Super Armor sopra 60 per una settimana 43,5%; Indice Armor 37,0%;
Indice crollo 33,5%.
Calo del 3% entro una settimana (base 9,8%): Indice Armor sopra 60 per un mese 30,0%; Super Armor 30,3%;
Indice crollo 23,8%.

Il 64,2% dell'Indice Armor su sei mesi è il numero più alto ma poggia su **cinque episodi**: va guardato
con molta prudenza. Il più solido è l'Indice crollo con 68 episodi, che però dà il numero più basso.

## 7. Risposte dirette alle domande dell'utente
- **I valori sono più precisi?** Sì su un punto: la scala dell'Indice Armor ora distingue quattro zone
  invece di schiacciarsi sotto 56. No sul resto: la precisione del segnale non è aumentata, è stata
  misurata meglio, e in diversi casi era sopravvalutata.
- **L'Indice Armor funziona meglio?** È più leggibile, non più preciso. Nessuna delle modifiche provate
  (fondi a breve, Buffett, radar sistemico, settore rotto) l'ha migliorato.
- **Il Super Armor lavora meglio?** Sì per la persistenza: sopra 60 per una settimana dà il numero più
  alto fra i tre con un numero decente di episodi (54,8% su 17).
- **L'Indice crollo è superiore all'Indice Armor?** **A una settimana sì, nettamente**: le prime otto
  posizioni della gara sono sue. A un mese e a tre mesi nessuno dei due funziona fuori campione.

## 8. Cosa è andato nell'app
Scheda **«Quadro di oggi»** in cima a Oggi: i tre indici con il loro colore e quante delle ultime cinque
sedute sono state sopra 60, poi il solo segnale promosso (la settimana) con il numero misurato. Per un
mese e tre mesi la scheda dice che **non c'è un segnale affidabile**, invece di mostrare il meno peggio.
Gli approfondimenti stanno in un pannello che si apre.
