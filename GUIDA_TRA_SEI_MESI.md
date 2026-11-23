# GUIDA PER IL FUTURO: obiettivo di Armor e tutti i dati che si accumulano

Scritta il 23 novembre 2026, da leggere prima di qualunque ricerca nuova (previsto: maggio 2027 o dopo). Chi legge sei tu, Claude, in una sessione nuova senza memoria: qui c'è tutto quello che serve per ripartire senza chiedere all'utente cose già dette.

## 1. L'obiettivo (non cambia)

L'utente (italiano, investe in VWCE e S&P 500 con un PAC su Trade Republic) vuole che l'app **avvisi in tempo di crisi e correzioni sistemiche di origine finanziaria**: mercato troppo esteso o caro, rendimenti in salita, credito che si restringe, liquidità che sparisce, leva che si scarica. **Non** gli interessano i crolli causati da fattori esterni (guerre, pandemie, dazi, geopolitica).

Le sue parole, che restano il metro di giudizio:
- «L'indice del crollo si accorge del crollo quando sta avvenendo; in questo sono bravo anch'io con i miei occhi.»
- «Deve avere un anticipo di almeno 24 ore. Il giorno prima di un crollo finanziario l'indice è spesso basso, quando dovrebbe avvertirmi che il mercato è molto predisposto al crollo.»
- «Se l'indice si alza il giorno stesso è troppo tardi. Quando la paura è alta il crollo sta già avvenendo: devi anticipare l'aumento della paura.»
- «Gli indici devono anticipare il mercato, non seguirlo: sfasa i confronti (valori di ieri/settimana scorsa per prevedere domani/settimana prossima/mese prossimo).»
- Numeri onesti, mai ritoccati per far quadrare. Spiegazioni semplici, senza sigle, in italiano. Procedure per PowerShell (aperto da solo, non il terminale di VS Code) e Chrome, un passo alla volta.

Come si lavora: **protocollo scritto prima, scelta sul passato (fino al 2014), verifica su dati mai visti (dal 2015), soglia del «migliore tra N tentativi» contro la fortuna, esito scritto anche se negativo.** Mai adottare qualcosa perché «sembra funzionare» sull'intero periodo.

## 2. Dove eravamo il 23 novembre 2026

- **Indice crollo** (src/armor/indice_crollo.py): 12 «famiglie» di segnali, pesi tarati sul passato; dà 1–100 (fasce: fino a 35 verde, 36–40 grigio, 41–60 giallo, 61–80 rosso, 81–100 viola). **È in gran parte reattivo**: le famiglie veloci (paura, curva della volatilità, tendenza, perdita dal massimo) pesano il 71%, la sola paura il 39%. Il giorno prima di 14 crisi finanziarie storiche l'indice era sotto 41 in 11 casi. Nessuna variante migliore è risultata adottabile (ESITO_ANTICIPO.md, ESITO_SFASATO.md).
- **Unico segnale che anticipa davvero** (a 5 giorni): il livello del VIX misurato al giorno T0 (AUC 0,69 / 0,78 contro una soglia di rumore di 0,74). A settimane o mesi **nulla è dimostrabile** con i dati storici che abbiamo: il passato utilizzabile è esaurito, per questo ora si accumula in avanti.
- **Terreno fragile** (src/armor/predisposizione.py): media di percentili di fragilità (CAPE, Indice Buffett, margin debt, credito, curva, liquidità…). È una *predisposizione*, non un allarme. Registrata ogni giorno in `data/predisposizione_registro.csv` per la verifica in avanti. Il 23/11/2026 valeva 66 (media).
- **Spia «mercato caro che sta già scendendo»** (spia_caro.py): CAPE alto × prezzo sotto la media a 200 giorni. L'unica ricerca libera (32 candidati, solo finanziari) che ha passato la verifica: nel 19% dei giorni col punteggio più alto, il −8% a 3 mesi è avvenuto nel 38,7% dei casi contro il 7,7%. Informativa, **non** parte dell'Indice crollo. Oggi «Forte».
- Registri giornalieri che non si riscrivono mai (servono alla verifica in avanti): `indice_crollo_registro.csv` (indice + tutte le famiglie), `predisposizione_registro.csv`, `crisi_lente_registro.csv`, `inclinazione_registro2.csv`, `grandi_fondi_badge_registro.csv`. **Il giorno zero della verifica in avanti è il 23/11/2026**: tutto ciò che nasce dopo questa data è fuori campione per costruzione.

## 3. Cosa si registra (inventario completo)

Lo scrive il workflow GitHub **«Accumulo dati per le ricerche future»** (22:50 e 06:50 UTC nei giorni di Borsa, gruppo di concorrenza `armor-dati`), codice in `src/armor/accumulo.py` e `src/armor/accumulo_extra.py`, comando `python -m armor accumulo [passi]` (passi: yahoo ohlc fred cboe_putcall intraday opzioni componenti bce ofr tesoro_curve tesoro_cassa_aste cot wikipedia cripto nyfed tsa finra gdelt). **Esito di ogni giro: `data/accumulo_stato.json`** (per ogni fonte: richieste, riuscite, fallite). Controllalo per primo: una fonte che manca da settimane va riparata o tolta.

Tutte le serie giornaliere stanno in `data/series/<id>.csv` (colonne `date,value`; si leggono con `store.load(id)`). Prefisso = fonte.

| Prefisso / cartella | Contenuto | Storia |
|---|---|---|
| (senza prefisso, ~220 file) | Le serie che l'app già usa: S&P 500 e VWCE, VIX e curva, MOVE, SKEW, put/call, CAPE, P/E, Buffett, margin debt, spread di credito, NFCI, bilancio Fed, curva dei rendimenti, indicatori lavoro/inflazione, COT sintetici, GPR, EPU, Fear&Greed, settori, ecc. | lunga (spesso dagli anni '80-'90) |
| `x_<simbolo>` | Chiusura giornaliera Yahoo di ~300 strumenti: indici USA/esteri, volatilità (VIX1D, VXN, OVX, GVZ, correlazione implicita, VVIX, VIX9D/3M/6M), ETF per paese/settore/fattore, obbligazioni e credito (breve→lungo, IG/HY, emergenti, municipali, inflazione), 30 cambi, materie prime e futures, criptovalute, banche estere, ETF a leva/volatilità | dalla prima data disponibile (1987–2021) |
| `xv_<simbolo>` | Volumi giornalieri degli stessi (solo titoli/ETF, non indici) | dal 2015 |
| `ohlc/<simbolo>.csv` | Apertura, massimo, minimo, chiusura, volume di 52 strumenti chiave (indici, VIX, ETF principali, settori, future, cambi, bitcoin) | dal 2000 |
| `f_<codice>` | ~330 serie FRED: tutte le scadenze dei Treasury, reali, inflazione attesa, SOFR/EFFR, spread ICE per rating, credito bancario e standard di prestito, bilancio Fed, RRP/repo, TGA, swap line, finestra di sconto, term premium, stress (STLFSI, KCFSI, OFR), lavoro (sussidi, JOLTS, Indeed), consumi, produzione, case, regionali, debito, cambi, tassi esteri, materie prime | dalla prima data disponibile |
| `cboe_pc_<nome>` | Put/call CBOE: totale, azioni, indici, S&P 500, VIX, ETF | storico dove c'è, poi giornaliero |
| `bce_<nome>` | **CISS** (indice di stress sistemico della BCE: area euro, Italia, Germania, Francia, Spagna, USA, Regno Unito, Cina), curve euro AAA e tutti gli emittenti (2/10/30 anni), tassi BCE, cambi euro | CISS dal ~1990, curve dal 2004, tassi BCE dal 1999 |
| `ofr_<nome>` | OFR Financial Stress Index e le sue 5 componenti (credito, valutazioni azionarie, finanziamento, beni rifugio, volatilità) | dal 2000 |
| `ust_curva_*`, `ust_bills_*`, `ust_reali_*`, `ust_reali_lungo_*` | Curve ufficiali del Tesoro USA, ogni scadenza (nominali, bill, reali) | dal 1990/2003 |
| `fisc_tga_milioni`, `fisc_debito_pubblico` | Conto del Tesoro presso la Fed (quando sale, drena liquidità) e debito pubblico giornaliero | dal 2005 / 2000 |
| `aste/aste.csv` | Aste dei titoli di Stato USA: domanda (bid-to-cover), rendimento, chi compra (dealer/diretti/esteri) | dal 1990 |
| `cot/tff.csv` | CFTC «Traders in Financial Futures»: posizioni di dealer, gestori, fondi speculativi, altri (ES, Nasdaq, Russell, VIX, Treasury, valute, bitcoin) | dal 2006, settimanale (martedì, pubblicato venerdì) |
| `wiki_<articolo>` | Visite giornaliere di Wikipedia a 42 voci (Stock market crash, Recession, Bank run, Margin call, Silicon Valley Bank, Credit crunch…) = attenzione del pubblico | dal luglio 2015 |
| `gdelt_<tema>_volume/_tono` | Quanto e con che tono i media mondiali parlano di crollo, recessione, crisi bancaria, stretta di credito, default, inflazione, licenziamenti, panico | solo ultimi 3 mesi a ogni giro, poi cresce |
| `cripto_*` | Totale stablecoin in circolazione (liquidità cripto), TVL DeFi, indice paura/avidità cripto | dal 2017–2018 |
| `nyfed_{sofr,tgcr,bgcr}_*` | Tassi overnight garantiti, percentili (1, 25, 75, 99) e volumi: la coda alta (p99 − mediana) segnala tensione nel finanziamento | ultimi ~1500 giorni, poi cresce |
| `tsa_passeggeri` | Persone ai controlli aeroportuali (economia reale, giornaliero) | dalla finestra pubblicata, poi cresce |
| `finra_short/AAAA-MM.csv` | Vendite allo scoperto giornaliere (short, esenti, totale) per ogni titolo S&P 500 e ETF chiave + totale di mercato | recupera 60 giorni per giro all'indietro fino a ~2,5 anni |
| `intraday/AAAA-MM/AAAA-MM-GG.csv.gz` | Barre a **5 minuti** (UTC; colonne sym,ts,o,h,l,c,v) di 52 strumenti | **solo da 23/11/2026** (Yahoo ne dà 5 giorni) |
| `opzioni_ext/AAAA-MM.csv` | Per ogni scadenza di SPY, QQQ, IWM, TLT, HYG, GLD, USO, XLF, S&P 500 e VIX: volumi e posizioni aperte call/put, put/call, volatilità al centro, asimmetria 25-delta, gamma netta (GEX) | **solo da 23/11/2026** |
| `componenti/{close,vol}_AAAA-MM.csv.gz`, `elenco.csv` | Chiusure e volumi di tutte le 503 aziende dell'S&P 500 (colonne = titoli), con settore | dal 2015 |
| `archive/` | Catene di opzioni SPY (`chains/`), bilanci (`fundamentals/`), `live_daily.csv`: archiviati dall'app da prima | vedi i file |
| altri file dell'app | `grandi_fondi/` (13F), `aziende.json`/bilanci SEC, revisioni utili, brevetti, calendario eventi, ecc. | vedi CONTINUA_DA_QUI.md |

### Cosa è «retroattivo» e cosa solo «in avanti»
- **Con storia lunga, usabile subito**: x_, xv_ (dal 2015), ohlc, f_, bce_, ofr_, ust_, fisc_, aste, cot, wiki_ (dal 2015), componenti (dal 2015), finra (progressivo).
- **Solo da oggi, non ricostruibile**: intraday a 5 minuti, opzioni_ext, gdelt (oltre i 3 mesi), nyfed oltre 1500 giorni, tsa oltre la finestra. Fra sei mesi saranno ~125 giorni di Borsa: **abbastanza per studiare relazioni quotidiane, quasi certamente non per verificare un crollo vero** (può non essercene nessuno nel campione).

## 4. Trappole note (leggile prima di analizzare)

1. **Mai guardare l'intero periodo.** Regola ≤2014 scelta, ≥2015 verifica. Con dati nuovi (intraday, opzioni) il «passato» è solo il 2026-27: vale la regola «scelta sulla prima metà, verifica sulla seconda», con soglia del migliore-tra-N (rimescolare i bersagli a blocchi d'anno/mese, 1000 volte).
2. **Pochi eventi.** Gli episodi finanziari sono ~11–14 in 35 anni, correlati fra loro. Con meno di ~10 eventi indipendenti non si «dimostra» nulla. Usa anche bersagli continui (drawdown massimo dei 5/21/63 giorni successivi, salto del VIX, volatilità realizzata futura) e dillo chiaramente.
3. **Il perimetro «solo finanziario»** è già codificato nelle ricerche (finestre ESTERNI e MISTE_MAX in src/armor): riusale, non reinventarle. Escluse: Covid 2020, guerra/Ucraina, dazi, ecc.
4. **Anticipo vs coincidenza.** Un segnale che sale insieme al calo (come la paura) dà AUC alta ma non serve. Ogni test deve usare valori **ritardati** (T−1, T−5, T−21) e partire da «mercato fermo» (non già in calo). L'errore fatto in passato è stato proprio questo.
5. **Date e pubblicazione.** FRED: molte serie mensili escono con settimane di ritardo e vengono riviste: usa un ritardo di pubblicazione (le ricerche usano lag 50–90 giorni per margin debt e Buffett). COT: la data è il martedì, uscita il venerdì → disponibile dal lunedì dopo. FINRA short: file del giorno T disponibile la sera. Wikipedia: attesa 1–2 giorni.
6. **Chiusure Yahoo** sono quelle non corrette per i dividendi (ETF obbligazionari «perdono» il dividendo). Per i rendimenti usa differenze logaritmiche con cautela o i tassi veri. Future, cambi e criptovalute: la barra del giorno è parziale e viene salvata dal giorno dopo; fusi diversi → allinea per data di borsa.
7. **Componenti S&P 500**: elenco di oggi, quindi *sopravvivenza* (chi è uscito non c'è). Va bene per ampiezza di mercato recente (quanti titoli sopra la media a 50/200 giorni, nuovi minimi, dispersione, correlazione media), non per backtest di lungo periodo.
8. **File grandi**: mai riscrivere ogni giorno file compressi (gonfiano la storia di git). Intraday è già per giorno; componenti per mese (≈300 KB). Se cresce troppo, passa a trimestre o sposta su un altro deposito.
9. **Fonti fragili** (provate solo sul runner, non dal sandbox): GDELT (limite 1 richiesta ogni 5 secondi), TSA (pagina web, può cambiare), CFTC (colonne), OFR (URL), Tesoro (URL). Se `accumulo_stato.json` mostra errori fissi, correggi il parser.
10. **Rumore e tentativi.** Con ~700 serie nuove e centinaia di trasformazioni, qualcosa «funzionerà» per caso. Conta il numero di tentativi e usa la soglia del migliore-tra-N, altrimenti sei in autoinganno.

## 5. Che cosa cercare con questi dati (piano a sei mesi)

Ipotesi, **da scrivere in un protocollo con data prima di guardare i risultati**:
- **Liquidità e finanziamento**: TGA + RRP + riserve (f_wtregen, f_rrpontsyd, f_wresbal, fisc_tga_milioni), coda dei tassi overnight (nyfed_*_p99 − mediana), aste deboli (bid-to-cover basso, coda alta), swap line usate (f_swpt), finestra di sconto (f_wlcflpcl). Domanda: il drenaggio di liquidità precede i cali di settimane?
- **Stress sistemico non americano**: CISS Italia/Germania/Francia/area euro, spread BTP-Bund (da curve tutti gli emittenti vs AAA), OFR FSI. Domanda: lo stress europeo o dei rendimenti anticipa quello americano?
- **Posizionamento e leva**: COT (dealer vs fondi speculativi sul VIX e sui future ES), margin debt, short volume FINRA (aumento della quota di vendite allo scoperto prima dei cali?), ETF a leva/inversi (volumi xv_ di SQQQ, TQQQ, UVXY, VXX). Domanda: la posizione affollata precede l'inversione?
- **Ampiezza e dispersione** dai componenti: percentuale di titoli sopra media 50/200 giorni, nuovi minimi/massimi a 52 settimane, correlazione media fra titoli, dispersione dei rendimenti, quota di rialzo dovuta ai primi 10 titoli, settori che divergono. Domanda: il mercato regge su pochi titoli prima dei cali?
- **Forma della volatilità**: VIX1D, VIX9D, VIX3M, VIX6M, VVIX, SKEW, VXN, correlazione implicita (COR1M/3M/6M), skew 25-delta e GEX da opzioni_ext. Domanda: l'inclinazione/gamma negativa precede l'accelerazione?
- **Intraday**: ampiezza (alto-basso) a 5 minuti, ultime due ore della seduta, gap di apertura, divergenza fra ES=F (notturno) e SPY, volume nei primi 30 minuti, correlazione intraday azioni-obbligazioni-dollaro. Domanda: la struttura della giornata cambia il giorno prima dei cali?
- **Attenzione del pubblico**: Wikipedia (Margin call, Bank run, Credit crunch) e GDELT (tono media). Domanda: l'attenzione sale prima o durante?
- **Rischio sotto traccia**: banche (KRE, KBE, banche estere DB/UBS/BCS), credito privato e high yield (HYG, JNK, BKLN, BIZD), emergenti (EMB, EMLC), mutui/CRE (f_drsfrmacbs, f_drcclacbs…), cripto come termometro della liquidità (stablecoin, bitcoin).
- **Aggregato**: ritenta «Terreno fragile» e le famiglie dell'Indice crollo con 5–10 nuove famiglie, **solo** se passano la verifica in avanti (dati dopo 23/11/2026 a formula ferma) o la verifica ≥2015 con la regola del migliore-tra-N.

Procedura suggerita: (1) leggere questa guida, ESITO_SFASATO.md, ESITO_ANTICIPO.md, ESITO_RICERCA_LIBERA.md e i PROTOCOLLO relativi; (2) controllare `accumulo_stato.json` e i buchi nei dati; (3) scrivere PROTOCOLLO_<nome>.md con ipotesi, bersagli, soglie, numero di tentativi; (4) eseguire con codice nuovo in uno script, salvare il json dei risultati; (5) scrivere ESITO_<nome>.md anche se negativo; (6) adottare in app **solo** ciò che soddisfa le regole del protocollo; (7) aggiornare CONTINUA_DA_QUI.md e specchiare i documenti nel Project «Armor».

## 6. Dati che desidereremmo e non abbiamo (gratis non c'è, o è fragile)

Da cercare/aggiungere se diventano raggiungibili: curva dei future VIX (strutture a termine, contango/backwardation) e posizionamento sui future VIX giornaliero; CDS e indici CDX/iTraxx; basis cross-currency (EUR/USD, USD/JPY) e spread degli swap; fails-to-deliver SEC e prestito titoli; flussi giornalieri di ETF e fondi (ICI, EPFR); AAII e NAAIM (sondaggi degli investitori); dealer inventories e posizioni primarie (NY Fed, settimanale); bid-ask e profondità nel mercato dei Treasury; emissioni obbligazionarie societarie e IPO/lock-up; vendite di insider (SEC Form 4, raccolta aggregata); riacquisti di azioni proprie e finestre di blocco; perdite non realizzate delle banche (FDIC trimestrale); ipoteche commerciali e credito privato (marcature); posizione speculativa sul carry trade yen; Google Trends («stock market crash», «recession», «layoffs»); indici ad alta frequenza dell'economia reale (traffico merci su ferrovia, camion, consumo di elettricità, prenotazioni ristoranti); mercati di previsione (Polymarket/Kalshi, probabilità di recessione); dati su Italia e BTP-Bund giornalieri affidabili (le curve BCE ci danno il lato euro).

## 7. Promemoria operativo

- Repo GitHub `Stefo818/armor`, locale `/home/claude/armor` nelle sessioni cloud; app su GitHub Pages; cache dell'app in `web/sw.js` (alzare il numero a ogni modifica visibile; ultimo noto: armor-v88).
- Test: `PYTHONPATH=src python3 -m pytest -q` (278+ test). Compilare anche con `/usr/bin/python3.11` (un f-string con barra rovesciata ha già rotto i workflow): `python3.11 -c "import glob;[compile(open(f).read(),f,'exec') for f in glob.glob('src/armor/*.py')]"`.
- Salvataggio dati dai workflow: `scripts/salva.sh "messaggio" <percorsi>`; il gruppo `armor-dati` serializza i workflow per evitare conflitti.
- File con righe CRLF/miste: report.py, jobs.py, sources.py — modificare via byte, non con il testo di Python.
- L'utente dopo ogni spinta deve rilanciare, da GitHub → Actions: «Accumulo dati per le ricerche future», poi «Aggiornamento giornaliero Armor», poi «Sito Armor (prezzi live e app per telefono)», e riaprire l'app.
- Ogni cosa mostrata all'utente: italiano semplice, senza sigle, con la «chiave di lettura».
