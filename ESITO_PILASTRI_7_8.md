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

---
# Parte 4 — Tutti i cali forti degli ultimi 40 anni, e la causa di ciascuno
Rilevati dai dati (calo di almeno l'8% dal massimo precedente, dal 1986): **23 episodi**. La causa di
ognuno viene dalla cronaca e dalle fonti ufficiali, **non** dal comportamento del modello.

| massimo | calo | natura | causa documentata |
|---|---|---|---|
| 1986-09-04 | −9,4% | finanziaria | timori su inflazione e tassi, vendite automatiche dei programmi |
| 1987-08-25 | −33,5% | finanziaria | lunedì nero: assicurazione di portafoglio e vendite automatiche |
| 1989-10-09 | −10,2% | finanziaria | crollo delle obbligazioni spazzatura, crisi delle casse di risparmio |
| 1990-07-16 | −19,9% | **esterna** | invasione del Kuwait, shock del petrolio |
| 1994-02-02 | −8,9% | finanziaria | rialzo a sorpresa dei tassi, l'anno del massacro delle obbligazioni |
| 1997-02-18 | −9,6% | finanziaria | timori di stretta monetaria |
| 1997-10-07 | −10,8% | finanziaria | crisi finanziaria asiatica |
| 1998-07-17 | −19,3% | finanziaria | default russo e crollo del fondo a leva LTCM |
| 1999-07-16 | −12,1% | finanziaria | stretta della banca centrale americana |
| 1999-12-31 | −9,2% | finanziaria | tassi in salita e valutazioni tirate |
| 2000-03-24 | −49,1% | finanziaria | scoppio della bolla tecnologica |
| 2007-07-19 | −9,4% | finanziaria | prime perdite sui mutui, crisi dei fondi quantitativi |
| 2007-10-09 | −56,8% | finanziaria | crisi dei mutui e del credito |
| 2015-05-21 | −14,2% | mista | svalutazione cinese, crollo del petrolio con contagio sul credito |
| 2018-01-26 | −10,2% | finanziaria | scoppio dei prodotti scommessi sulla volatilità bassa |
| 2018-09-20 | −19,8% | mista | stretta della banca centrale più guerra dei dazi |
| 2020-02-19 | −33,9% | **esterna** | pandemia |
| 2020-09-02 | −9,6% | finanziaria | rientro delle scommesse a leva sulle opzioni dei titoli tecnologici |
| 2022-01-03 | −25,4% | finanziaria | inflazione e stretta (il grosso del calo precede l'invasione dell'Ucraina) |
| 2024-07-16 | −8,5% | finanziaria | rientro del carry trade sullo yen dopo il rialzo dei tassi giapponesi |
| 2025-02-19 | −18,9% | **esterna** | dazi e guerra commerciale |
| 2026-01-27 | −9,1% | **esterna** | attacchi USA-Israele contro l'Iran e blocco dello stretto di Hormuz |
| 2026-10-06 | −11,6% | finanziaria | rivalutazione dei titoli dell'intelligenza artificiale, inflazione, rendimenti |

**17 finanziarie, 4 esterne, 2 miste.**

**Esclusione che mancava.** L'episodio di febbraio-marzo 2026 era dentro il campione «finanziario» per
errore: le fonti lo attribuiscono all'escalation con l'Iran dopo gli attacchi di fine febbraio. È stato
aggiunto alle finestre di shock esterno (2026-02-25) e tutti i conti sono stati rifatti.

Due conferme utili dalla ricerca: agosto 2024 è **finanziaria** (rientro del carry trade sullo yen, cioè
leva che si smonta) e il 2022 resta finanziaria perché il grosso del calo arriva prima dell'invasione
dell'Ucraina.

# Parte 5 — La scala dell'Indice Armor, tarata
Trasformazione monotona: non cambia l'ordine dei giorni, quindi non cambia nessuna AUC, nessuna prova e
nessun risultato pubblicato. Sposta solo i confini. Punti di aggancio: i percentili dell'Indice Armor
sulle sole crisi finanziarie dal 1986 che corrispondono a 40, 60 e 80 del Super Armor, cioè **39,43**,
**49,82** e **56,83** della scala vecchia.

Frequenze misurate dopo la taratura (8.187 giorni, sole crisi finanziarie; base: calo al 10% entro 60
sedute nel 26,8% dei casi, −5% entro 10 sedute nel 7,0%):

| fascia | giorni | quota | il calo arriva al 10% | si perde il 5% entro 10 sedute |
|---|---|---|---|---|
| sotto 40 · tranquillo | 4.877 | 59,6% | 12,9% | 2,9% |
| **40-60 · in difficoltà** | 2.792 | 34,1% | **39,8%** | 10,7% |
| **60-80 · in pericolo** | 452 | 5,5% | **85,4%** | 23,0% |
| **sopra 80 · rischio di crollo** | 66 | 0,8% | **100,0%** | 42,4% |

Le etichette richieste dall'utente sono quindi **confermate dai dati**, con un avvertimento: i 66 giorni
sopra 80 sono raggruppati in due o tre episodi, quindi quel 100% vale come «sempre, nei pochi casi
visti», non come una legge.

**Oggi l'Indice Armor passa da 50,2 a 61,0**, cioè entra in «pericolo». Il valore grezzo resta salvato
nella colonna `armor_index` e continua ad alimentare i calcoli interni di probabilità, che erano tarati
su quella scala: cambiare il numero a monte li avrebbe rotti in silenzio.

# Parte 6 — L'articolo su P/E, CAPE e indice Buffett
Nessuna integrazione necessaria: tutti e tre sono già nel modello. P/E (`pe_m`) e CAPE (`cape_m`) sono
nella famiglia «Valutazioni» dell'Indice Armor da prima; l'indice Buffett è stato aggiunto oggi come
candidata. Il limite che l'articolo stesso segnala — un CAPE alto non significa che il mercato crollerà
domani, e può restare alto per anni — è esattamente ciò che le misure di questo progetto mostrano:
l'indice Buffett ha la discriminazione più alta fra i segnali strutturali (0,6710) ma non migliora
l'Indice Armor su nessuno dei tre eventi.
