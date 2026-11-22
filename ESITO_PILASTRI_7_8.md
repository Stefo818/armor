# Esito — Pilastri «fondi a breve» e indice Buffett, e taratura delle soglie
Regole: `PROTOCOLLO_PILASTRI_7_8.md`, pubblicato prima dei calcoli (commit 98befeb).

## 1. L'osservazione dell'utente era giusta: c'era un buco vero
Titan ha sei pilastri e il quarto dice «cosa fanno i grandi fondi». Ma `titan_job.py` gli passa **una
sola** serie: `cot_am_net`, cioè i **gestori di patrimoni**, gli investitori a **lungo** termine. I
**fondi con leva** (`cot_lev_net`), che sono quelli a breve termine e che vendono per primi, non entrano
da nessuna parte. E l'indice Buffett non c'era.

Misurato nella zona entro il 5% dai massimi (sole crisi finanziarie, bersaglio: il calo arriva al 10%
entro 60 sedute, base 9,3%):

| candidata | AUC | precisione del quinto più alto | oggi |
|---|---|---|---|
| **C1 fondi a breve in uscita** | 0,5414 | **21,5%** | **96 su 100** |
| C2 divergenza breve contro lungo | 0,5239 | 9,9% | 85 |
| **C3 indice Buffett** | **0,6710** | 20,0% (dal 1999) | **99 su 100** |
| *quello già nel modello: fondi a lungo in uscita* | **0,4579** | 13,4% | 4 |
| riferimento: Indice crollo attuale | 0,7095 | 21,5% | — |

Tre cose. La serie che Titan usa oggi ha AUC **0,4579**, cioè sotto il caso. I fondi a breve, ignorati,
hanno nel loro quinto più alto la stessa precisione dell'indice intero. L'indice Buffett ha l'AUC più
alta di qualunque segnale strutturale provato finora, meglio delle valutazioni classiche (0,6157).
La **divergenza** fra breve e lungo, cioè l'ipotesi nella sua forma più precisa, non funziona.

## 2. Prova A: la regola di adozione già scritta nel progetto
Ogni candidata si aggiunge alla sua famiglia e si confronta l'Indice Armor con e senza, sui tre eventi dal
2013. Si adotta solo se migliora di almeno 0,01 in **almeno 2 eventi su 3** senza peggiorarne nessuno.

| candidata | evento −10%/63g | evento −5%/21g | evento volatilità | esito |
|---|---|---|---|---|
| fondi a breve | +0,0117 | +0,0041 | −0,0003 | migliora 1 su 3 → **non adottata** |
| indice Buffett | +0,0035 | +0,0018 | +0,0026 | migliora 0 su 3 → **non adottata** |

**Nessuna delle due entra nell'Indice Armor** per la regola del progetto. Entrambe però superano P2, cioè
sono utili vicino ai massimi. Restano registrate come candidate: il test si rifà da solo ogni mese e le
adotterà senza interventi se col tempo se lo guadagnano. Non diventano un pilastro a sé: per farlo
servirebbe ritarare i sei pilastri esistenti, e il protocollo lo vieta in questa prova.

Correzione tecnica trovata strada facendo: gli indicatori «solo percentile» mandavano in errore il test di
adozione (`_thresh_score` riceveva soglie vuote). Era un buco del codice che avrebbe colpito qualunque
candidata di quel tipo. Corretto.

## 3. Le soglie 40 / 60 / 80 richieste dall'utente
Misurato su tutte le crisi finanziarie dal 1990. Frequenze di base: il calo arriva al 10% entro 60 sedute
nel 26,6% dei casi; si perde il 5% entro 10 sedute nel 7,0%.

**Indice Armor** (oggi 50,2) — la scala è schiacciata:

| fascia | giorni | quota | −10% entro 60 sedute | −5% entro 10 sedute |
|---|---|---|---|---|
| sotto 40 | 5.184 | 62,8% | 13,2% | 3,1% |
| 40-60 | 3.069 | 37,2% | 49,1% | 13,6% |
| 60-80 | **0** | — | — | — |
| sopra 80 | **0** | — | — | — |

Il 99° percentile dell'Indice Armor è **56,4**: sopra 60 non ci arriva **mai**. Le fasce «pericolo» e
«crollo imminente» chieste dall'utente oggi sono **irraggiungibili**, ed è per questo che il numero sembra
dire poco.

**Super Armor** (oggi 55,2) — qui la scala funziona già:

| fascia | giorni | quota | −10% entro 60 sedute | −5% entro 10 sedute |
|---|---|---|---|---|
| sotto 40 | 4.915 | 59,6% | 14,2% | 3,0% |
| 40-60 | 2.823 | 34,2% | 36,2% | 10,6% |
| 60-80 | 450 | 5,5% | **90,4%** | 20,0% |
| sopra 80 | 65 | 0,8% | **100,0%** | **58,5%** |

Le soglie chieste dall'utente, per il Super Armor, sono **confermate dai dati**: sopra 60 il calo al 10% è
arrivato nel 90% dei casi, sopra 80 in tutti. Attenzione però: i 65 giorni sopra 80 sono pochi e
raggruppati in due o tre episodi, quindi quel 100% vale come «sempre, nei due o tre casi visti», non come
una legge.

**Conclusione operativa:** non serve cambiare il Super Armor, serve **ridistendere la scala dell'Indice
Armor**, che è una trasformazione monotona — non cambia nulla di ciò che il modello sa, cambia solo dove
cadono i confini. Allineando i percentili dell'Indice Armor a quelli del Super Armor, i confini 40 / 60 /
80 cadrebbero intorno a 38,5 / 48,8 / 57 della scala grezza di oggi.
