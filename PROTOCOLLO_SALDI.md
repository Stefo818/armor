# PROTOCOLLO «SALDI» — versione 1, datato 10 novembre 2026

Scritto prima di qualsiasi verifica. I pesi sono il **punto di partenza**: si cambiano al massimo una volta l'anno e solo se la tabella «Quanto ha funzionato il punteggio» (rendimenti reali a 1 e 3 mesi, registro `data/saldi_registro.csv`) lo giustifica. L'impronta di questo file va in `data/protocollo_saldi_log.csv`.

## Cosa misura il punteggio
«Salute e probabilità di recupero stimate», da 1 a 100. 100 = azienda in ottima salute, calo con cause che storicamente si riassorbono; 1 = gravissime difficoltà. **Non** è una previsione di rimbalzo e non è un consiglio di acquisto.
Basi documentate: inversione di breve periodo (Jegadeesh 1990, Lehmann 1990; Chan 2003: i perdenti senza notizie recuperano, quelli con notizie continuano); deriva dopo i risultati (Bernard e Thomas 1989); momentum a 3-12 mesi (Jegadeesh e Titman 1993) con eccezione per aziende solide e a buon prezzo (Piotroski 2000).

## Componenti e pesi
| componente | peso | voci |
|---|---|---|
| Solidità finanziaria | 30% | Altman Z (o Z''), copertura interessi, debito netto/EBITDA, current ratio, mesi di cassa, diluizione |
| Qualità e tendenza | 25% | F-score, crescita del fatturato a/a, margine lordo, margine FCF, ROE |
| Natura del calo | 20% | causa dalle notizie: settore/mercato o nessuna notizia = positivo; aumento di capitale, declassamento = leggermente negativo; risultati sotto attese, previsioni tagliate = negativo (peso pieno nei periodi ≤ 1 settimana, dimezzato oltre); rifiuto FDA o studio fallito = molto negativo |
| Valutazione dopo il calo | 15% | P/S, P/E, P/S previsto, EV/EBITDA, in percentile nel settore (se almeno 8 titoli) o nell'insieme |
| Segnali di fiducia | 10% | acquisti degli insider, raccomandazione media, short interest, distanza del prezzo obiettivo |

## Calcolo
- Ogni voce è un percentile nell'insieme dei candidati (valori tagliati al 2%-98%). Voci mancanti: non contano. Componente = media dei percentili × 100; punteggio grezzo = media pesata delle componenti disponibili (pesi rinormalizzati; servono almeno 2 componenti).
- Punteggio finale = `1 + 99 × percentile` del punteggio grezzo nell'insieme dei candidati.
- **Tetti a 15/100**: dubbio sulla continuità aziendale nelle notizie; 8-K item 1.03, 3.01 o 4.02; rapporto di uno short seller con accuse di frode; mesi di cassa < 6.
- **Esclusi** dalla lista: società oggetto di acquisizione già annunciata.
- Ogni titolo ha accanto «Dati usati: n componenti su 5». Senza dati sufficienti: nessun punteggio.

## Verifica continua
Ogni giorno si registrano i 30 titoli più calati per periodo con punteggio e componenti. Dopo 21 e 63 sedute si calcolano rendimento a 1 e 3 mesi e confronto con S&P 500 (SPY), per fascia di punteggio (1-20 … 81-100). Il test storico con dati SEC per data di deposito (dal 2012) **non è ancora stato eseguito**; quando lo sarà dirà che è ottimista (solo titoli ancora quotati).
