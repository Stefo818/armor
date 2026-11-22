# Esito — Indice crollo

Regole: `PROTOCOLLO_INDICE_CROLLO.md` (commit 973f665) e il suo emendamento 1 sulle sole crisi
finanziarie (commit a728989), entrambi pubblicati **prima** di questi calcoli.
Etichetta pre-registrata: **«Non coerente»**. Non si usa la parola «provato».

## 1. Cosa è stato provato
Tutti e cinque i modelli della parte 4, più l'Indice Armor come riferimento. Scelta sui dati 1990-2014,
prestazione riportata sul 2015-2026, mai usato per scegliere.

Giorni con bersaglio dal 1990: 9.290. Esclusi 760 giorni di shock esterni (dazi, guerre, pandemia,
attentati) e 277 giorni delle due crisi miste. Restano **8.253 giorni** di sola natura finanziaria.
Frequenza del bersaglio (−5% nel minimo delle 10 sedute successive): 8,0% su tutto, **7,0%** sul solo
sottoinsieme finanziario.

Scelta (1990-2014, area sotto la curva sul bersaglio primario):

| modello | AUC |
|---|---|
| M2 composito a pesi fissati | 0,7759 |
| M5 regola a due chiavi | 0,7729 |
| M1 media semplice | 0,7724 |
| M3 regressione logistica | 0,7301 |
| M4 alberi potenziati | 0,6251 |
| **Indice Armor (riferimento)** | **0,7774** |

Vincente fra i modelli nuovi: **M2**. Ma il riferimento già esistente è il migliore di tutti.

## 2. Verifica sul 2015-2026 (periodo mai usato per scegliere)
- M2: AUC **0,7545**, intervallo al 90% [0,6326, 0,8465], placebo 95° percentile 0,6383, con le crisi
  miste incluse 0,7334 (R5 rispettata).
- Indice Armor: AUC 0,7336, intervallo [0,5957, 0,8209], con le miste 0,7507.
- Frequenza di base nel periodo: 4,4%.

Regole di accettazione: **R1 sì, R2 no, R3 sì, R4 sì, R5 sì** → **«Non coerente»**.
Cade R2: la fascia viola avrebbe dovuto mostrare almeno 2,5 volte il rischio di base e invece mostra
7,3% su soli 41 giorni (per l'Indice Armor 0,0% su 21 giorni). Con così pochi giorni in fascia viola nel
sottoinsieme finanziario, quella fascia non dice nulla di affidabile. Va detto così.

Frequenze per fascia (M2, verifica, sole crisi finanziarie):

| fascia | giorni | quota | crollo poi |
|---|---|---|---|
| verde | 1.484 | 69,0% | 1,9% |
| grigio | 130 | 6,0% | 2,3% |
| giallo | 334 | 15,5% | 11,1% |
| rosso | 161 | 7,5% | 14,3% |
| viola | 41 | 1,9% | 7,3% (troppo pochi giorni) |

## 3. Il numero che serve per decidere, e quello che inganna
Due numeri vengono spesso confusi. Dal 1990, sole crisi finanziarie:
- **Sensibilità:** fra i giorni seguiti da un calo al 10%, l'indice era giallo o peggio nell'**82,5%** dei
  casi. È il numero che fa sembrare bravo il modello.
- **Precisione:** dopo un giorno giallo o peggio, il calo è poi arrivato nel **59,4%** dei casi, e questa
  cifra è gonfiata dai giorni già in piena discesa.

La precisione pulita, divisa per quanto il mercato era già scivolato, è la vera chiave di lettura:

| situazione | giorni | il calo arriva al 10% | intervallo 90% |
|---|---|---|---|
| entro il 2% dal massimo, indice verde o grigio | 3.569 | 5,5% | [3,2 – 7,6] |
| entro il 2% dal massimo, indice giallo o peggio | 299 | 11,7% | [3,4 – 21,1] |
| fra il 2% e il 7% sotto, indice verde o grigio | 1.227 | 6,5% | [2,7 – 10,1] |
| **fra il 2% e il 7% sotto, indice giallo** | 644 | **23,0%** | [13,5 – 31,3] |
| **fra il 2% e il 7% sotto, indice rosso o viola** | 378 | **28,0%** | [16,7 – 41,0] |

**Qui sta l'unico uso solido dell'indice:** quando il mercato è già scivolato fra il 2% e il 7% sotto il
massimo, una lettura gialla o peggiore distingue 23-28% contro 6,5%, cioè circa quattro volte il rischio.
Vicino ai massimi distingue poco (11,7% contro 5,5%) e con un intervallo che sfiora il nulla.

Episodi di allarme distinti dal 1990 sul sottoinsieme finanziario: **229**, di cui **61** seguiti da un calo
del 10% e **168 falsi allarmi**.

## 4. Il risultato più importante: agire sull'indice avrebbe fatto perdere soldi
Verifica dal 2015, sole crisi finanziarie, decisione presa con il valore del giorno prima.

| regola | risultato | restando investito | giorni fuori mercato | perdita peggiore |
|---|---|---|---|---|
| esco su rosso e viola | +142,7% | +235,6% | 9,4% | −33,9% (uguale) |
| esco solo su viola | +164,4% | +235,6% | 2,0% | −33,9% (uguale) |
| esco su giallo o peggio | +63,6% | +235,6% | 21,9% | −35,1% (peggiore) |

Nessuna versione protegge: la perdita peggiore resta identica o peggiora, e il rendimento si riduce di
molto. Il motivo si vede nei rendimenti successivi per fascia: le letture alte arrivano **durante** il
panico, cioè vicino ai minimi, non prima.

| fascia | 10 sedute dopo (mediana) | positivi | 21 sedute dopo (mediana) | positivi |
|---|---|---|---|---|
| verde | +0,66% | 65% | +1,30% | 70% |
| giallo | +1,25% | 63% | +2,79% | 70% |
| rosso | +2,95% | 72% | +4,91% | 68% |
| viola | +2,05% | 66% | +5,97% | 90% |

## 5. Gli 11 episodi finanziari, uno per uno
L'indice al massimo precedente era **basso in tutti**: 1,1 nel 2018, 2,6 nel 2015, 5,5 nel 2022, 10,3 nel
2007, 10,8 nel 2026, 45,6 nel 2000. **I crolli non si vedono dalla cima.**
Poi sale: a −2% dal massimo la mediana è 49,5 (giallo o peggio in 8 casi su 10); a −5% la mediana è 74,9
(giallo o peggio in **10 casi su 10**). Attenzione: questi due ultimi numeri sono sensibilità, non
precisione — vanno letti insieme alla tabella della parte 3.

Quando il mercato era già oltre il 7% sotto il massimo, contando **per episodio** e non per giorno:
dei **9** episodi finanziari che hanno superato quel punto, **3 sono arrivati a un calo del 20%** e 6 si
sono fermati fra il 10% e il 19%, cioè **33%**. Contando per giorno veniva 68%, ma quel numero è gonfiato
dai due mercati lunghi (2000-2002 e 2007-2009) che da soli valgono centinaia di giorni: il conteggio per
giorno è sbagliato per questa domanda e non va usato.

## 6. Le due date opposte, e il percorso di questo episodio
| data | indice | fascia | sotto il massimo | crollo nei 10 giorni dopo |
|---|---|---|---|---|
| 6 ottobre 2026 (il massimo) | 10,8 | verde | 0,0% | no |
| 30 ottobre | 41,3 | giallo | −3,1% | no |
| **5 novembre** | **72,3** | **rosso** | −5,9% | **no (falso allarme)** |
| 13 novembre | 42,7 | giallo | −3,3% | sì |
| **18 novembre** | **66,2** | **rosso** | −6,3% | **sì** |
| 19 novembre | 73,4 | rosso | −8,2% | no |
| 20 novembre | 78,9 | rosso | −11,6% | in corso |

Il 5 novembre l'indice era **più alto** del 18 novembre e non è seguito nulla. L'indice **non sa
distinguere** i due casi, e questo è il limite da tenere presente. Quello che sa fare è segnalare che la
fase è fragile: dal 16 ottobre in poi i suoi allarmi sono stati tutti corretti, mentre fra il 2 marzo e
l'8 aprile 2026 c'era stato un falso allarme durato 27 sedute.

## 7. Cosa è stato messo nell'app
Scheda **Indice crollo** in cima a Oggi, con le fasce e i colori richiesti (fino a 35 verde, 36-40 grigio,
41-60 giallo, 61-80 rosso, 81-100 viola). Il testo cambia secondo quanto il mercato è già scivolato,
perché lo stesso numero significa cose diverse nelle tre zone.

Le parole «crollo molto probabile» **non** sono state usate: la regola della parte 8 del protocollo le
consente solo sopra il 50% misurato, e il massimo misurato è 28%. Al loro posto la scheda riporta la
frequenza vera. La scheda dichiara di non aver superato la prova, non manda notifiche e dice
esplicitamente che un numero alto non è un invito a vendere.

## 8. Limiti
Undici episodi finanziari dal 1990, sei dei quali prima del 2001: ogni cifra ha un margine ampio e un
singolo episodio pesa molto. La fascia viola ha troppo pochi giorni nel sottoinsieme finanziario per dire
qualcosa. Le serie di ampiezza del mercato, i differenziali ad alto rendimento e l'indice di paura e
avidità hanno meno di due anni di storia nell'archivio e non sono entrati nella validazione (provati a
parte: area sotto la curva fra 0,56 e 0,62, e 0,30 per paura e avidità, cioè al contrario). I dati
gratuiti arrivano con ritardo. Un indice tarato su undici casi non può funzionare «alla perfezione»: la
cosa più onesta che può fare è distinguere il 23-28% dal 6,5% nella zona in cui serve.

---
# Parte 9 — Quattro tentativi di migliorare l'indice (emendamenti 2, 3, 4)
Ipotesi dell'utente: in ogni crisi finanziaria il settore guida, il più forte e il più indebitato, cede
**prima** che l'indice scenda. Provata sulla zona **entro il 5% dai massimi**, bersaglio: il calo arriva al
10% sotto il massimo a 12 mesi entro 60 sedute. Frequenza di base della zona: **9,3%**.
Riferimento da battere: l'Indice crollo attuale nella stessa zona fa **21,5%** (810 giorni, intervallo al
90% [13,3 – 28,6], area sotto la curva 0,7095).

## Tentativo 1 (emendamento 2) — il settore guida come «migliore a 24 mesi»: fallito
| famiglia | AUC |
|---|---|
| valutazioni storicamente alte | 0,6157 |
| premio per il rischio azionario basso | 0,6022 |
| oro in fuga rispetto alle azioni | 0,5894 |
| insolvenze delle imprese in peggioramento | 0,5887 |
| tecnologia tirata rispetto al resto | 0,5678 |
| pochi settori sopra la media a 200 giorni | 0,5611 |
| tassi reali e curva | 0,5409 |
| debito a margine degli investitori | 0,5354 |
| **il settore guida cede mentre l'indice tiene** | **0,5185** |
| liquidità del sistema in calo | 0,4615 |
| credito alle imprese in espansione | 0,4138 |
| **il settore guida smette di guidare** | **0,3570 (al contrario)** |
La definizione era sbagliata: «migliore a 24 mesi» dava **materiali** nel 2007, mentre il settore che si è
rotto era la **finanza**, che già perdeva da mesi. Per il 2000 non dava nessun settore.

## Tentativo 2 (emendamento 3) — «un settore importante è già rotto»: fallito
| segnale | AUC | precisione nel quinto più alto |
|---|---|---|
| dispersione fra settori | 0,6555 | 13,2% |
| il settore più rotto | 0,6160 | 12,6% |
| composito «assetto sistemico» | 0,6468 | **18,5%** |
| **riferimento: indice attuale** | **0,7095** | **21,5%** |
R10 (serviva 25%) e R13 (serviva battere di 8 punti) non superate → **«Non coerente»**.
La regressione logistica con esclusione di un episodio alla volta è crollata a 0,2447, cioè peggio del
caso e rovesciata: con dodici variabili e sei episodi il modello impara il rumore.

**Errore mio, corretto.** Avevo calcolato R11 misurando la precisione solo nei giorni vicini all'episodio
escluso, dove il bersaglio è vero quasi per costruzione: i valori 42-87% erano circolari e sono annullati.
Rifatta come doveva (soglia senza l'episodio, precisione su tutta la zona): **18,2%**.

**Però la descrizione dell'utente è esatta.** In **6 episodi su 6** un settore importante era già rotto
nei 120 giorni prima che l'indice perdesse il 10%:
| episodio | settore più rotto | quanto sotto il suo massimo a 6 mesi |
|---|---|---|
| 2000 | materiali | −27,9% |
| 2007 | **finanza** | −24,6% |
| 2015 | energia | −27,1% |
| 2018 | servizi pubblici | −15,6% |
| 2022 | consumi discrezionali | −17,4% |
| 2026 | **tecnologia** | −26,2% |
Ma è **sensibilità**, non precisione: la stessa condizione si presenta spesso senza che segua nulla.

## Tentativo 3 (emendamento 4) — due chiavi: il risultato più interessante, e comunque non promosso
| regola | giorni | precisione | intervallo 90% | episodi con preavviso |
|---|---|---|---|---|
| **D1: indice nel quinto più alto + un settore rotto oltre il 15%** | 165 | **42,4%** | [23,8 – 70,7] | **3 su 6** |
| D2: indice nel quinto più alto + valutazioni nel quinto più alto | 404 | 20,5% | [9,8 – 34,3] | 1 su 6 |
| riferimento: solo indice nel quinto più alto | 810 | 21,5% | [13,3 – 28,6] | 6 su 6 |

D1 supera R15 (precisione sopra il 30% con limite inferiore sopra 21,5%) e R17, ma **cade su R16**:
servivano 4 episodi su 6 e ne prende 3. Etichetta pre-registrata: **«Non coerente»**.

I tre che prende sono **2000, 2007 e 2026**: esattamente i tre descritti dall'utente, le crisi in cui un
settore gonfio e indebitato si rompe per primo. I tre che manca sono 2015 (svalutazione cinese), 2018
(scoppio dei prodotti sulla volatilità) e 2022 (inflazione e tassi): crisi finanziarie che però **non**
hanno quella forma. L'ipotesi è quindi più **stretta** e più **affilata** di come era stata posta: vale
per un tipo di crisi, non per tutte.

Da pesare con onestà: 165 giorni concentrati in tre episodi valgono come **tre** osservazioni, non 165.
L'intervallo [23,8 – 70,7] lo dice. E questo è il **quarto** sguardo sugli stessi sei episodi: al quarto
tentativo qualcosa si trova anche per caso. Per questo D1 entra nell'app solo come riga descrittiva, con
il suo punto cieco scritto accanto, e la ricerca si chiude qui come previsto dal protocollo.

## Cosa è stato aggiunto all'app
Nella scheda Indice crollo una riga **«Settore più in difficoltà»** con il nome del settore e quanto sta
sotto il suo massimo a sei mesi. Quando il settore è rotto oltre il 15% **e** il mercato è ancora entro il
5% dai massimi **e** la tensione è alta, la riga dice che è l'assetto del 2000, 2007 e 2026, con il 42%
misurato, i 165 giorni su tre episodi e le tre crisi mancate. Oggi il settore più rotto è la
**tecnologia, 26% sotto il suo massimo a sei mesi**, ma il mercato è già all'11,6% sotto il suo: l'assetto
delle due chiavi si valuta vicino ai massimi, quindi oggi non si applica.

## Il dato che manca, e come si recupera
Nell'archivio **differenziale del credito ad alto rendimento** e **investment grade** partono dal novembre
2023: tre anni. È il taglio dell'accesso pubblico senza chiave di FRED, non un limite della fonte: la
serie vera parte dal **dicembre 1996** e coprirebbe tutti e sei gli episodi. È il canale di cui parla
l'utente — il debito delle aziende — e il glossario di Armor stesso lo chiama uno dei migliori segnali
anticipatori. Con quella storia il canale credito diventa verificabile; senza, no. Serve una chiave
gratuita FRED messa fra i segreti di GitHub (`FRED_API_KEY`): i due workflow la passano già.
Le misure citate dall'utente — valutazione dei primi dieci titoli, investimenti contro flusso di cassa
delle aziende di intelligenza artificiale — partono dal 7 novembre 2026 e restano non verificabili: i
bilanci storici si prendono dalla SEC, raggiungibile dai workflow su GitHub ma non da questo ambiente.
