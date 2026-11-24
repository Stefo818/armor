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
