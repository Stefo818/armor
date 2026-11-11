# PROTOCOLLO ARMOR v47 — motore Titan al posto di FHS+VIX e del vecchio Indice Armor
Scritto l'11 novembre 2026. Regole decise PRIMA di guardare dati nuovi.

## Cosa cambia (in parole semplici)
- Il motore di calcolo si chiama **Titan v47**. Calcola ogni giorno: Indice Armor, Super Armor (media di 6 pilastri), Radar del Decennio Perduto, probabilità di calo e di rialzo a 1 settimana, 1 mese, 3, 6 e 12 mesi.
- La scala resta quella di sempre: 1 = ottimo, 40 = ingresso in zona stress, 100 = pericolo massimo.
- **Fase 1 (fatta):** Titan gira ogni giorno e scrive `data/titan.json` e `data/titan_storia.csv`. Il vecchio indice è ancora quello mostrato.
- **Fase 2 (da fare):** l'indice mostrato nell'app passa a Titan, dopo aver visto i primi risultati giornalieri veri.

## Dati veri usati (non la cache di ricerca)
- Archivio dell'app `data/series` (aggiornato ogni giorno) e storia fissa `data/series_storia` (tassi, EBP, CAPE, P/E, P/S).
- Il credito usa solo lo spread BAA-10Y: `hy_oas` parte dal 2023 e spezzerebbe la serie.
- Nessun riempimento all'indietro (`bfill`): la ricerca usava dati del futuro nelle serie che partono tardi.
- Grandi fondi: margin debt e posizioni dei gestori (CFTC) se presenti; DIX/GEX e AAII non sono nell'app (AAII per licenza), valgono zero.

## Risultati con i dati veri (1994–2026; FHS+VIX → Titan)
| Orizzonte | Rischio di calo 1994-26 | Rischio 2013-26 | Direzione 1994-26 | Direzione 2013-26 |
|---|---|---|---|---|
| 1 settimana | 0,777 → 0,777 | 0,762 → 0,764 | 0,531 → 0,538 | 0,516 → 0,521 |
| 1 mese | 0,767 → 0,762 | 0,690 → 0,677 | 0,512 → 0,559 | 0,472 → 0,531 |
| 3 mesi | 0,686 → 0,723 | 0,626 → 0,656 | 0,518 → 0,600 | 0,473 → 0,556 |
| 6 mesi | 0,644 → 0,694 | 0,529 → 0,658 | 0,558 → 0,682 | 0,438 → 0,622 |
| 12 mesi | 0,560 → 0,659 | 0,477 → 0,675 | 0,558 → 0,695 | 0,496 → 0,608 |

Chiave di lettura: 0,50 = come tirare una moneta; più è alto, meglio il modello distingue i giorni a rischio. Oggi (10/11/2026): Indice Armor 44,0 · Super Armor 46,0 · Radar 77,7.

## Limiti dichiarati
- Pesi e soglie sono stati regolati in 47 versioni guardando gli stessi dati: i risultati sono ottimistici. Gli episodi di crollo indipendenti sono pochi (circa 5 dal 2000): a 6 e 12 mesi il vantaggio recente poggia su pochissimi eventi.
- A 1 settimana Titan è pari a FHS+VIX; a 1 mese il rischio è leggermente peggiore (la direzione è migliore).
- Non è consulenza finanziaria.

## Regole decise ora
1. **Serie:** restano tutte le serie previste. Una serie esce solo se peggiora l'AUC di più di 0,02 in almeno 3 orizzonti su 5, con la stessa prova. Mai scelta guardando solo i risultati migliori.
2. **Confronto dal vivo:** da oggi `data/titan_storia.csv` e il vecchio indice vengono registrati insieme; si guardano a ogni fine mese.
3. **Passaggio dell'indice mostrato (Fase 2):** dopo almeno 10 giorni di calcolo giornaliero senza errori e valori coerenti con la ricerca (differenza entro 2 punti sull'Indice Armor).
4. **Revisione dei pesi del motore:** non prima del 10/11/2027, o 90 giorni dopo il primo calo dell'S&P 500 di almeno il 10% (come PROTOCOLLO_INDICE_ARMOR).
5. **Dati futuri:** il test automatico `tests/test_titan.py` verifica che ricostruire l'indice con la storia tagliata dia lo stesso valore di quel giorno.

## Impronta dei file (SHA-256, righe a capo normalizzate)
| File | SHA-256 |
|---|---|
| `src/armor/titan.py` | `6531adf5a1e318bb8abfa26c6cd8c906db3b73ec1b900e1e49fb2bd9693a0f64` |
| `src/armor/titan_dati.py` | `25ea9a3f48de75613c2637240ffe6f0418eda7aedfccef235f2a65c3f6fbf0e8` |
| `src/armor/titan_job.py` | `2a2294eadba6101f143d830762a51856858753910f5253056a344e3643348871` |
| `tests/test_titan.py` | `46628db70ae6ed3710acd8cc79518e102713366c197989e254359dbd13b96792` |
| `scratch/verifica_titan_reale.py` | `30b08e3de408f50f0ee788cf9203b51d9137bff66798d064ac856072c3098c2d` |
| `data/series_storia/cape.csv` | `a80cd27a07f18abbacf73755a3afbf0670818b2c704189e851ccb4d55b3331b3` |
| `data/series_storia/ebp.csv` | `97720ad65a5d15b314d411dba84c1a4de7bc7e912ea9d55e861dd7b3abf346ca` |
| `data/series_storia/hy_oas.csv` | `d64b3bbec2e7c27d5f2837b76e46441dedd74403a6fd40a025cdd3ad759c0627` |
| `data/series_storia/pe.csv` | `e0b641b4dee9b6d547983f8f71008e50e1128d2ec29aa45ef8e264b535a814f0` |
| `data/series_storia/ps.csv` | `0d0d7fce9f95413ab7b3b99de12f824347528d77e47ea8a616ab026ae8896e51` |
| `data/series_storia/y10y.csv` | `a355afc045f2b4a45ab5437b08e0c132369a8340d88fbc567f9bada9f7d68ab0` |
| `data/series_storia/y3m.csv` | `d8dfad36b558f05a2d67a4738d9df642e4a65ec20dba505303af5c45b6b514ca` |
| `data/series_storia/y5y.csv` | `99313825586e8011147203e9d761da5168d31a718b300f698d2417ddf72f61e5` |

**Impronta complessiva:** `30be91a8cc04127a6bca6167617adb092b2de9db2936591ff8244cff799329f7`
