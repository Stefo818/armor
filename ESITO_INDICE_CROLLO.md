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

---
# Parte 10 — Il canale credito: perché i dati non ci sono e cosa c'è al loro posto
**Non è un bug e non è la chiave mancante.** La chiave FRED era già configurata da due settimane. Il
recupero storico è stato lanciato e ha funzionato per tutte le altre serie, ma i due differenziali del
credito sono rimasti a tre anni.

La diagnosi (comando `python -m armor fred_test`): senza chiave FRED restituisce i mutui a 30 anni
**dal 1971** (2.904 righe) ma i differenziali ICE BofA solo **dal 21 novembre 2023** (786 righe). Non è
un limite generale di FRED: è una **restrizione di licenza di ICE**, che consente a FRED di ridistribuire
pubblicamente solo gli ultimi tre anni di quegli indici. Da quella fonte la storia lunga non esiste, con
o senza chiave.

**Un bug però c'era davvero, ed è stato corretto.** In `sources.update_all` l'opzione «scarica tutto
dall'inizio» era rispettata per le serie di borsa ma non per quelle FRED: queste chiedevano sempre gli
ultimi 14 mesi se la serie era già presente. Ora è corretta, è stato aggiunto il comando
`python -m armor storico` e il workflow «Recupero storico dati FRED». Serve per il futuro, non per questo
caso.

**Il canale credito era già nel modello, con una storia più lunga.** Il differenziale Moody's Baa meno
titoli di Stato è in archivio **dal 1986** (10.221 righe) e copre tutti e 11 gli episodi finanziari,
mentre i differenziali ICE partono comunque solo dal 1996. Misurato nella zona entro il 5% dai massimi
(quinto sguardo, esplorativo):

| segnale di credito | storia | AUC | precisione nel quinto più alto |
|---|---|---|---|
| differenziale Baa, variazione a 20 sedute | dal 1986 | 0,6251 | 17,2% |
| differenziale Baa, variazione a 60 sedute | dal 1986 | 0,6066 | 15,2% |
| differenziale Baa, livello | dal 1986 | 0,5002 | 14,0% |
| obbligazioni rischiose contro sicure, 60 sedute | dal 2007 | 0,5283 | 12,6% |
| obbligazioni rischiose contro sicure, 120 sedute | dal 2007 | 0,4779 | 6,4% |
| **riferimento: Indice crollo attuale** | | **0,7095** | **21,5%** |

Il credito che si allarga in fretta è il miglior singolo segnale strutturale trovato finora (0,6251,
più di valutazioni e oro), ma da solo resta sotto l'indice completo, che lo contiene già come una delle
dodici famiglie. Conclusione: avere i differenziali ICE dal 1996 non avrebbe cambiato l'esito.

---
# Parte 11 — Il buco del credito, chiuso da altre fonti. La conclusione non cambia.
Domanda: esistono altri posti da cui prendere la storia lunga del credito rischioso? Sì, tre.

| fonte | cosa dà | storia | preso? |
|---|---|---|---|
| Yahoo, fondo Vanguard High-Yield Corporate (VWEHX) | il prezzo di un vero fondo che presta alle aziende rischiose | **dal 1980**, giornaliera | **sì** |
| FRED, Moody's giornaliero Baa e Aaa (DBAA, DAAA) | rischio di credito puro, senza la parte dei tassi | dal 1986 e 1983 | **sì** |
| Federal Reserve Board, «excess bond premium» di Gilchrist e Zakrajšek | la misura che usano gli studiosi per questa esatta domanda | dal 1973, mensile | non presa: il sito non è raggiungibile da questo ambiente, lo sarebbe dai workflow |

Aggiunte all'archivio cinque serie nuove: `hy_fondo` (11.819 righe dal 1980), `gov_fondo` (11.695 dal
1980), `ig_fondo` (11.819 dal 1980), `baa_d` (10.257 dal 1986), `aaa_d` (11.016 dal 1983). Il fondo
rischioso dal 1980 copre **tutti** gli episodi finanziari, cioè più degli indici ICE, che partirebbero
comunque dal 1996.

Risultato nella zona entro il 5% dai massimi (sesto sguardo, esplorativo):

| segnale di credito | dal 1999, base 9,3% | dal 1990, base 8,0% |
|---|---|---|
| fondo rischioso, caduta dal massimo a 1 anno | 0,6216 (quinto 16,3%) | 0,5787 (11,2%) |
| scarto Baa meno Aaa, variazione a 20 sedute | 0,6104 (10,2%) | 0,5786 (7,7%) |
| fondo rischioso contro sicuro, 120 sedute | 0,6002 (13,5%) | 0,5702 (11,1%) |
| fondo rischioso contro sicuro, 60 sedute | 0,5932 (16,0%) | 0,5924 (14,2%) |
| scarto Baa meno Aaa, livello | 0,4227 (3,1%) | 0,4826 (6,0%) |
| **riferimento: Indice crollo attuale** | **0,7095 (21,5%)** | **0,6844 (15,8%)** |

Quattro misure di credito indipendenti — Baa meno Stato, Baa meno Aaa, fondo contro fondo, caduta del
fondo rischioso — cadono tutte fra 0,58 e 0,62. Il credito è un segnale vero ma di quella forza, e
l'indice completo, che lo contiene già, resta sopra. **Avere i dati ICE dal 1996 non avrebbe cambiato
nulla:** ora lo so per misura e non per congettura, perché la storia lunga ce l'ho da un'altra porta.

Correzioni tecniche fatte nel passaggio: tempo di attesa su FRED portato da 25 a 60 secondi (le serie
Moody's giornaliere sono grandi e andavano in timeout) e spiegazioni aggiunte al glossario per le cinque
serie nuove.

---
# Parte 12 — Correzioni dopo l'audit esterno (documento GPT/Gemini del 22 novembre 2026)
L'audit solleva due critiche precise al codice di questo progetto. **Hanno ragione entrambe.** Sotto, la
verifica e i numeri corretti. Le conclusioni pubblicate non cambiano, ma l'incertezza sì: era sottostimata.

## 1. I pesi di M2: il protocollo era ambiguo, il codice ha scelto una lettura
Il protocollo scrive «paura e curva della paura 0,30; credito 0,15; tendenza e perdita in corso 0,25;
rotazione difensiva 0,15; tassi 0,15 (normalizzati a 1)». Letta per **gruppo** la somma fa esattamente
**1,00**, il che spiega la nota «normalizzati a 1»; letta per **variabile** fa 1,55. Il codice aveva usato
la seconda. L'audit legge la prima ed è la lettura più probabile.

| lettura | AUC scelta 1990-2014 | AUC verifica 2015-2026 | fascia viola |
|---|---|---|---|
| A, un peso per variabile (codice pubblicato) | 0,7759 | **0,7545** | 5,5% su 55 giorni |
| B, il peso è del gruppo (lettura dell'audit) | 0,7719 | **0,7546** | 4,9% su 41 giorni |

**La differenza è di 0,0001.** L'ambiguità non ha spostato nulla e nessuna conclusione cambia. Restano
pubblicate entrambe, come chiede l'audit; il risultato già registrato non viene sostituito.

## 2. Il bootstrap della tabella per fascia era rotto
Confermato. Con 41 giorni in fascia viola, `per_fascia()` estraeva blocchi di 21 osservazioni partendo
solo dalla prima metà dell'array: restituiva frequenza 7,3% e intervallo [9,5 – 14,3], che non contiene
nemmeno la stima. Numero impossibile, già segnalato nella parte 2 di questo esito e ora corretto alla
radice: ricampionamento ad **anni interi** su tutto il campione, con la frequenza di fascia ricalcolata
dentro ogni ricampionamento.

| fascia | giorni | anni con dati | crollo poi | intervallo 90% corretto |
|---|---|---|---|---|
| verde | 1.467 | 12 | 1,8% | [0,6 – 3,9] |
| grigio | 119 | 10 | 2,5% | [0,0 – 6,4] |
| giallo | 331 | 11 | 10,9% | [4,1 – 17,6] |
| rosso | 178 | 9 | 14,0% | **[0,0 – 20,5]** |
| viola | 55 | 5 | 5,5% | [0,0 – 6,4] |

Gli intervalli veri sono molto più larghi di quelli pubblicati: per la fascia rossa il limite inferiore è
**zero**. R2 resta non superata (servirebbe 10,9% in viola) e l'etichetta «Non coerente» regge, ora su
basi più solide.

## 3. Quante osservazioni indipendenti ci sono davvero
L'audit avverte che 8.253 sedute non sono 8.253 osservazioni. Misurato: i blocchi contigui di bersaglio
vero sono **145** dal 1990 e **27** nel periodo di verifica. La dimensione effettiva del problema è
quella, non il numero di righe.

## 4. Le metriche operative che mancavano (verifica 2015-2026)
| soglia | giorni in allarme | quota dei giorni | precisione | richiamo | giorni di falso allarme |
|---|---|---|---|---|---|
| giallo o peggio | 564 | 26,2% | 11,3% | **68,1%** | **500** |
| rosso o viola | 233 | 10,8% | 12,0% | 29,8% | 205 |
| solo viola | 55 | 2,6% | 5,5% | 3,2% | 52 |

Il quadro onesto in una riga: con la soglia gialla l'indice **prende due terzi dei cali veri** ma sta in
allarme un giorno su quattro e accumula 500 giorni di falso allarme in undici anni.

## 5. Il preavviso, misurato per la prima volta
È la metrica che l'audit chiede («lead time per episodio») ed è anche la domanda iniziale dell'utente.
Quante sedute prima che il calo arrivasse al 10% l'indice è entrato in giallo:

| episodio | primo giallo | sedute di anticipo |
|---|---|---|
| 1990 | mai prima | 0 |
| 1997 | 7 ottobre | 15 |
| 1998 | 21 luglio | 19 |
| 1999 | 20 luglio | 51 |
| 2000 (aprile) | 24 marzo | 16 |
| 2000 (ottobre) | 24 marzo | 140 |
| 2007 | 19 ottobre | 26 |
| 2015 | mai prima | 0 |
| 2018 | 2 febbraio | 5 |
| 2022 | 18 gennaio | 25 |
| **2026** | **16 ottobre** | **26** |

**Mediana 25 sedute, con preavviso in 9 episodi su 11.** Va letto insieme ai 500 giorni di falso allarme
della tabella sopra: prende quasi tutti i cali veri proprio perché si accende spesso. Questo numero è
sensibilità, non precisione.

## 6. Cosa è stato fatto, e cosa no
**Fatto:** corretti bootstrap e pesi, aggiunte le metriche operative e il preavviso alla scheda (sempre
accanto al suo costo), e introdotto `data/indice_crollo_registro.csv`, un **registro che non si riscrive
mai**: ogni giorno salva indice, fascia, zona, settore rotto, le dodici spinte e la firma della versione
dei pesi.

Il registro è la raccomandazione più importante dell'audit ed è anche la conclusione a cui portano queste
sei analisi: sugli stessi undici episodi il passato ha detto tutto quello che poteva dire, e ogni nuovo
tentativo aumenta solo la probabilità di trovare qualcosa per caso. **L'unica prova non inquinata è in
avanti, a formula ferma.**

**Non fatto, di proposito:** nessuna architettura «v5» a tre livelli. L'audit la propone, ma le misure di
questo progetto dicono che il livello strutturale è debole vicino ai massimi (0,52-0,62 contro 0,71
dell'indice intero) e l'audit stesso vieta di promuovere qualunque cosa senza verifica prospettica.
Costruire ora un sistema più grande significherebbe aggiungere complessità prima di avere le prove per
sceglierla. La mossa corretta è tenere ferma la formula e lasciare che il registro accumuli mesi.
