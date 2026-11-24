# Protocollo: «territori di rischio endogeno» (convergenza di meccanismi)

Scritto il **24/11/2026 (pomeriggio)**, prima di calcolare un solo risultato. Nessuna regola si cambia dopo aver visto i numeri.

## La richiesta dell'utente
Oltre al Sovraccarico, l'app deve avvisare quando ci si avvicina alle **cause scatenanti** dei crolli *endogeni* (nati dentro il sistema finanziario: leva nascosta, affollamento su derivati, debito, liquidità che sparisce, credito, bolle di valutazioni, valute con debito estero), **mettendo in relazione più informazioni**: investitori troppo esposti a pochi settori che vogliono alleggerire, il mercato obbligazionario che drena soldi dall'azionario. L'app deve dire quando si entra in un «territorio» in cui, **in base al passato**, un crollo è molto più probabile.

## Metodo (identico alle ricerche precedenti)
Scelta delle regole sul passato fino al 2014, verifica su dati mai visti dal 2015, soglia del «migliore fra N tentativi», finestre di shock esterni escluse (ESTERNI, MISTE_MAX e 17/10/1973, come in PROTOCOLLO_CONCENTRAZIONE.md), nessun dato letto prima della sua data di pubblicazione (ritardi sotto), percentili sempre «espandenti» (solo passato).

## I sette meccanismi
Ogni indicatore è trasformato in percentile espandente (0-1, solo passato; minimo 252 giorni, o 60 mesi per dati mensili) con la direzione scritta qui: **più alto = più rischio**. L'indice di un meccanismo è la media dei suoi indicatori disponibili, poi di nuovo percentile espandente. Il meccanismo è **caldo** se l'indice è ≥ 0,80.

| # | Meccanismo (cosa ricorda dalla tabella) | Indicatori e direzione | Ritardo di pubblicazione |
|---|---|---|---|
| M0 | Concentrazione su pochi titoli/tecnologia (dot-com, Archegos) | livello di Sovraccarico (`concentrazione.calcola`, già registrato) | nessuno |
| M1 | Valutazioni da bolla (Giappone 1990, dot-com) | CAPE alto; salita dell'S&P 500 a 3 anni alta | CAPE 30 gg; prezzi 0 |
| M2 | Leva e affollamento (LTCM, Volmageddon, Archegos) | NFCI-leva alto; debito di margine in crescita annua alta (dal 1997); VIX basso (compiacenza, direzione invertita); SKEW alto | 5 gg; 50 gg; 1 gg |
| M3 | Credito e banche (subprime, 1990) | spread Baa−10 anni in allargamento a 3 mesi; curva 10 anni−3 mesi invertita (direzione invertita); SLOOS: banche che irrigidiscono i prestiti; NFCI-credito alto | 1 gg; 1 gg; 45 gg; 5 gg |
| M4 | Il mercato obbligazionario drena soldi dall'azionario (2018, 2022) | rendimento 10 anni salito a 12 mesi; premio per il rischio azionario basso (100/CAPE − rendimento 10 anni, direzione invertita); crescita annua di M2 bassa (direzione invertita); stretta della banca centrale (fedfunds a 12 mesi) | 1 gg; 30 gg; 30 gg; 1 gg |
| M5 | Debito sovrano e banche europee (2010-12) | stress sistemico dell'area euro (CISS) alto e salito a 3 mesi | 1 gg |
| M6 | Valute e debito estero (Asia 1997) | dollaro (DXY) salito a 12 mesi; salito a 3 mesi | 1 gg |

Dove un indicatore non esiste ancora (es. margine prima del 1997, VIX prima del 1990, SLOOS prima del 1990) il meccanismo usa gli altri; se non ne ha nessuno, il meccanismo non è disponibile quel giorno e non conta né come caldo né come freddo.

## Convergenza e stati da testare (N = 13, fissati ora)
K = numero di meccanismi caldi (sui disponibili). Stati:
- K2: K ≥ 2; K3: K ≥ 3; K4: K ≥ 4.
- Sette stati «meccanismo singolo» M0…M6 caldo.
- Tre combinazioni legate alle cause della tabella: **BOLLA = M1 e M0**; **LEVA = M2 e M3**; **DRENAGGIO = M4 e (M2 o M3)**.

## Bersagli (3)
Minimo dell'S&P 500 nei giorni successivi rispetto alla chiusura del giorno: B1: −8% entro 63 sedute; B2: −12% entro 63 sedute; B3: −15% entro 126 sedute.

## Misure
Differenza di rischio DR = P(bersaglio | stato) − P(bersaglio | non stato), sui giorni validi. Intervallo al 90% con ricampionamento per anno (400 giri). Blocchi: 1971-1989 (descrittivo), **1990-2014 (scelta)**, **2015-2026 (verifica)**. Soglia «migliore fra N»: 500 spostamenti circolari casuali dello stato (≥ 3 anni), si prende il DR massimo fra tutti i 13 stati × 3 bersagli nel blocco di verifica, 95° percentile.

## Regole di giudizio
Uno stato è **«dimostrato»** solo se, per almeno 2 bersagli su 3: (a) estremo inferiore dell'IC90 > 0 sia nel 1990-2014 sia nel 2015-2026; (b) DR di verifica ≥ soglia del migliore-fra-N; e inoltre (c) almeno 6 episodi indipendenti (accensioni a più di 126 sedute l'una dall'altra) su tutto il periodo e (d) **DR > 0 anche senza il 1973-75**. È un **«indizio»** se DR > 0 in entrambi i blocchi per almeno 2 bersagli e DR di verifica ≥ soglia, ma manca (a), (c) o (d). Altrimenti **«non supportato»**.
Cattura degli episodi: per ciascun evento della tabella (picchi dell'S&P 500: 16/07/1990, 07/10/1997, 17/07/1998, 24/03/2000, 09/10/2007, 23/04/2010, 29/04/2011, 26/01/2018; e, non nella tabella ma endogeni finanziari, 25/08/1987, 09/10/1989, 20/09/2018, 03/01/2022) si guarda se lo stato era acceso almeno un giorno nelle 126 sedute fino al picco incluso. Archegos (marzo 2021) non ha causato un calo dell'S&P 500 e non è valutabile. Si conta anche in quanti giorni lo stato è acceso (frazione) per mostrare quanto spesso suona.
Valore aggiunto: per gli stati dimostrati o indizio, DR nei giorni in cui l'Indice crollo è sotto 41 (dove oggi non avvisa).

## Cosa entra nell'app, deciso ora in funzione dell'esito
- Stato **dimostrato**: avviso forte (banda rossa nel Quadro di oggi, con meccanismi caldi in italiano semplice e probabilità storica).
- Stato **indizio**: avviso giallo «territorio da tenere d'occhio», con la dicitura «indizio, non dimostrato».
- **Non supportato**: nessun avviso; i meccanismi restano visibili come informazione (chip caldo/freddo), senza dire che «è probabile un crollo».
In ogni caso: registro giornaliero (`data/territori_registro.csv`) per la verifica in avanti, peso zero sull'Indice crollo.

## Limiti dichiarati
Indicatori americani e un solo europeo; pochi episodi, correlati; valori di mercato (margin debt, SLOOS) a bassa frequenza e riveduti; meccanismi con dati solo recenti (cot, put/call, intraday, flussi) non entrano perché non c'è storia. Gli eventi esterni (guerre, pandemie, dazi) sono esclusi per scelta.

## Note di attuazione (scritte prima di calcolare, per scelte che il testo lasciava aperte)
- **Curva dei tassi**: per avere la stessa serie dal 1971 si usa «rendimento 10 anni − tasso della Fed» (dgs10 − fedfunds, entrambi giornalieri) invece di 10 anni − 3 mesi (che parte dal 1982).
- **SLOOS** è trimestrale: percentile espandente con minimo 20 osservazioni (5 anni).
- **Spread di credito in allargamento (M3)**: stessa costruzione di PROTOCOLLO_CONCENTRAZIONE.md (C1: variazione a 3 mesi, percentile; giornaliero dopo il 06/1986, mensile con ritardo di 35 giorni prima).
- **Crescita di M2** = variazione sui 12 mesi; **debito di margine** = variazione sui 12 mesi (mensile, dal 1997).
- «Percentile espandente» = posizione del valore nell'insieme di tutti i valori fino a quel giorno (minimo 252 osservazioni giornaliere o settimanali, 60 mensili, 20 trimestrali).

## Addendum del 24/11/2026 ore 14:50 (dopo i due documenti aggiunti dall'utente; ancora nessun risultato calcolato)
**1. Le 4 cause profonde (documento dell'utente) come ponte con i meccanismi.** Leva e richieste di garanzie → M2 (+ M3); scadenze e liquidità non allineate (banche, fondi) → M3 e M4; bolle e sovrainvestimento → M1 e M0; affollamento e vendite tutte insieme → M0 e il VIX basso/SKEW in M2. Aggiunta di un indicatore a M2 per il carry trade sullo yen (agosto 2024): **«yen che si rafforza in fretta»** = 1 − percentile della variazione di 63 giorni del cambio dollaro/yen (dal 1996, ritardo 1 giorno).
**2. Nuovi eventi da catturare** (picchi dell'S&P 500, oltre a quelli già elencati): 02/02/2023 (banche regionali, SVB), 16/07/2024 (carry trade yen), 03/01/2022 già presente (tassi e fondi UK a settembre 2022 cadono dentro lo stesso calo). Non valutabili sull'S&P 500: FTX (cripto), Archegos, Flash Crash (rimbalzo in minuti), Giappone e Asia (mercati esteri; contano solo se spostano l'S&P 500: picchi 16/07/1990 e 07/10/1997 già inclusi). Novembre 2026 (correzione tech e AI in corso) **non entra nel verdetto** (il picco è il 06/10/2026 e l'esito è aperto): resta come caso vivo da guardare.
**3. Il modello a punteggio** (oltre agli stati a conteggio, che restano i 13 già fissati):
 - **Modello A (nessun adattamento)**: punteggio = media degli indici dei 7 meccanismi disponibili, poi percentile espandente (0-1).
 - **Modello B (adattato)**: regressione logistica con penalità (C = 0,1, variabili standardizzate), 7 indici dei meccanismi come ingressi, bersaglio B1, addestrata **solo su 1990-2014**, applicata di sera come probabilità sul 2015-2026 (nessun riaddestramento). Dati mancanti = valore mediano dell'addestramento.
 - Misura: area sotto la curva (AUC) sul 2015-2026 con intervallo al 90% (ricampionamento per anno), e DR dei giorni nel 10% di punteggio più alto (decile alto). Il confronto con il caso: spostamento circolare dei bersagli, 500 giri, 95° percentile dell'AUC. Si confrontano A e B con lo stesso bersaglio; le prove totali dichiarate salgono a **N = 13 stati × 3 bersagli + 2 modelli × 3 bersagli = 45**; la soglia «migliore fra N» si calcola su tutte e 45.
 - Il modello entra nell'app con la forza dei criteri già scritti: «dimostrato» solo con IC90 > 0 in entrambi i blocchi, AUC di verifica sopra la soglia del caso e ≥ 6 episodi indipendenti; altrimenti «indizio» o «non supportato».
**4. Soglia di allerta del modello**: decile alto del punteggio calcolato sul passato fino a quel giorno (percentile espandente ≥ 0,90). Fissata ora.

## Addendum del 24/11/2026 ore 14:55: modello «per tipo di crisi» (richiesta dell'utente; ancora nessun calcolo)
Idea dell'utente: ogni crisi e' diversa, quindi il modello deve riconoscere **quale** crisi si sta formando e pesare le variabili compatibili con quel tipo. Fissato ora, prima di vedere i dati:
- **Tipi e picchi assegnati (decisi qui, non modificabili):** CREDITO/BANCHE = 16/07/1990, 09/10/2007, 29/04/2011, 02/02/2023 · BOLLA = 24/03/2000, 03/01/2022 · LEVA/AFFOLLAMENTO = 17/07/1998, 26/01/2018, 16/07/2024 · VALUTE/ESTERO = 07/10/1997 · (1987 e 1989 non assegnati, restano nel controllo come «altro»).
- **Meccanismo compatibile di ogni tipo:** CREDITO → M3 (+M5); BOLLA → M1 (+M0); LEVA → M2 (+M0); VALUTE → M6. Il «modello per tipo» e' il massimo, giorno per giorno, dei punteggi dei tipi, ognuno calcolato solo con il proprio meccanismo (nessun peso adattato).
- **Test:** per ogni tipo, il suo meccanismo e' acceso (>= 0,80) nelle 126 sedute prima dei picchi di quel tipo piu' spesso che nelle 126 sedute prima di giorni casuali non-crisi (spostamenti circolari, 500 giri)? E il meccanismo di un tipo e' acceso prima dei picchi degli ALTRI tipi meno che prima dei propri (specificita')? Esito per tipo: «riconosce» solo se cattura >= 3 dei propri picchi, cattura meno degli altri e supera il 95° percentile del caso; con meno di 3 picchi per tipo (BOLLA, VALUTE) l'esito massimo e' «indizio».
- **Limite dichiarato:** 1-4 episodi per tipo: non basta per una prova statistica; serve a capire se l'idea merita di essere seguita in avanti. Se esce «non supportato» o «indizio», l'app mostra solo il tipo piu' compatibile con il clima di oggi, come informazione.

## Addendum del 24/11/2026 ore 15:30: Sick Index (richiesta dell'utente)
Il Sovraccarico viene unito ai prezzi da bolla perche' i due misurano la stessa cosa da lati diversi (correlazione fra i due indici 0,42 dal 1990; M1 acceso anche senza concentrazione, il 47% delle volte che la concentrazione e' alta M1 e' spento). **Indice Bolla** = percentile storico della media di M1 (prezzi da bolla) e M0 (concentrazione, ex Sovraccarico). **Indice Credito** = percentile storico della media di M3 (credito e banche) e M5 (stress debito europeo). Gli stessi meccanismi dei tipi BOLLA («indizio») e CREDITO («riconosce») gia' provati; la versione continua 0-100 non e' stata provata separatamente. Rosso da 80. In rosso l'app mostra i casi simili (300 giorni piu' vicini per livello e accelerazione a 63 sedute, dal 1990): salita massima e calo massimo tipici a 6 mesi. Peso zero; registro giornaliero (colonne bolla, credito).
