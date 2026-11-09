# PROTOCOLLO «OPPORTUNITÀ» — versione 1, datato 10 novembre 2026

Scritto prima di qualsiasi verifica. I pesi non si ottimizzano sui dati (rischio di sovra-adattamento): si cambiano al massimo una volta l'anno e solo se lo storico reale (`data/opportunita_registro.csv`) lo giustifica. L'impronta di questo file va in `data/protocollo_opportunita_log.csv`.

## Cosa misura
«Potenziale», 1-100: quanto un titolo somiglia, nei fattori documentati in letteratura, a quelli che storicamente hanno dato rendimenti futuri migliori. **Non** è una previsione del prezzo e non è un consiglio di acquisto.

## Filtri prima del punteggio
Capitalizzazione ≥ 300 milioni; controvalore medio ≥ 1 milione al giorno (20 sedute); almeno 3 analisti oppure dati SEC (RPO) disponibili; nessuna società oggetto di acquisizione annunciata; nessun tetto «grave» (8-K 1.03, 3.01, 4.02; dubbio di continuità). Pre-selezione: i 600 titoli con la migliore combinazione di momentum 12-1, vicinanza al massimo a 52 settimane, rendimento a 1 mese e volume relativo.

## Fattori e pesi
| fattore | peso | misura |
|---|---|---|
| Revisioni delle stime | 20% | variazione dell'EPS atteso a +1 anno a 30 e 90 giorni; rapporto revisioni su/giù negli ultimi 30 giorni |
| Momentum | 15% | rendimento a 12 mesi escluso l'ultimo mese; vicinanza al massimo a 52 settimane (George e Hwang 2004) |
| Crescita | 15% | crescita del fatturato a/a e sequenziale; «regola del 40» (crescita + margine di cassa) per il software. L'accelerazione trimestrale non è calcolabile con i soli 5 trimestri gratuiti |
| Qualità | 15% | margine lordo su attivo (Novy-Marx 2013), ROE, accruals bassi, F-score |
| Sorpresa e deriva | 10% | SUE dell'ultima trimestrale (sulla base delle ultime 4-8) |
| Contratti e visibilità | 10% | anni di fatturato già firmati (RPO), RPO/capitalizzazione, 8-K item 1.01 negli ultimi 90 giorni, contratti vinti nelle notizie in % del fatturato |
| Catalizzatori e temi | 10% | eventi positivi classificati negli ultimi 30 giorni (approvazione FDA, studio riuscito, contratto, partnership, previsioni alzate, promozioni) + forza del tema tecnologico |
| Valutazione ragionevole | 5% | P/S previsto diviso per la crescita (PSG), in percentile nel settore |

Ogni fattore è un percentile nel gruppo area+settore (se ha almeno 8 titoli) o nell'insieme. Voci mancanti non contano; servono almeno 4 fattori su 8. Somma pesata (pesi rinormalizzati) → percentile → `1 + 99 × p`.

## Fasce di crescita stimata (1 mese, 3 mesi, 1 anno, 2 anni)
Fascia, non promessa. Centro: rendimento mediano storico del mercato azionario (7% annuo, ipotesi dichiarata) finché il registro non ha almeno 30 scelte maturate a quell'orizzonte nella stessa fascia di punteggio; da allora il centro è la mediana reale di quelle scelte. Ampiezza: volatilità annua del titolo (media tra 63 e 252 sedute) × √t con quantili 10-90 di una distribuzione lognormale. Mostrata come «mediana, 8 casi su 10 tra X e Y». Sopra +100% si scrive in multipli, sempre con il limite inferiore.
Le fasce **non** incorporano il punteggio finché non c'è evidenza reale: oggi il punteggio ordina i titoli, non sposta il centro.

## Verifica
Ogni sabato si salvano le 30 scelte (prezzo, punteggio, fasce a 1 e 3 mesi). La pagina confronta il risultato reale con la fascia (verde se pari o sopra la mediana, rosso se sotto), il rendimento medio contro MSCI World (VT) e S&P 500 (SPY), la quota di titoli che battono VT e la quota di risultati dentro la fascia 10-90 (attesa vicino all'80%). Lo storico si mostra anche se negativo. Il test storico con bilanci SEC (2012-oggi) non è ancora stato eseguito.
