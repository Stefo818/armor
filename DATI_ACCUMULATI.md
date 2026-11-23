# Dati accumulati per le ricerche future (dal 23 novembre 2026)

> Guida completa con obiettivo, inventario aggiornato (anche BCE, OFR, Tesoro, CFTC, Wikipedia, GDELT, FINRA, NY Fed, TSA, cripto), trappole e piano di ricerca: **GUIDA_TRA_SEI_MESI.md**. Questo file è l'elenco originale delle prime fonti.

Scopo: fra qualche mese cercare correlazioni sui dati NUOVI con la regola «scelta sul passato, verifica in avanti» (vedi PROTOCOLLO_SFASATO.md). Nessuno di questi dati entra nei modelli o nelle schede: è solo archivio. Lo scrive il workflow «Accumulo dati per le ricerche future» (due volte al giorno nei giorni di Borsa), in modo indipendente dall'aggiornamento giornaliero: se una fonte fallisce, le altre continuano. Cosa è riuscito e cosa no: `data/accumulo_stato.json`.

| Categoria | Cosa | Dove | Storia |
|---|---|---|---|
| Indici e volatilità | Dow, Nasdaq, NYSE, Russell, S&P 400/600, trasporti, utilities, banche, semiconduttori; VIX 1 giorno, VXN, VXD, OVX, GVZ, correlazione implicita, VXTLT | series/x_*.csv | dal 1987–2011 secondo l'indice |
| Borse estere | Londra, Parigi, Madrid, Amsterdam, Zurigo, Stoccolma, Tokyo, Hong Kong, Corea, Taiwan, Australia, India, Brasile, Messico, Canada, Cina, Israele, Argentina | series/x_*.csv | dalla prima data disponibile |
| Paesi (ETF) | Giappone, Germania, Regno Unito, Francia, Italia, Spagna, Svizzera, Canada, Australia, Brasile, Messico, Corea, Taiwan, Hong Kong, Cina, India, Sudafrica, Turchia, Indonesia, Thailandia, Vietnam, Polonia, Argentina, Svezia, Olanda, Arabia, Emirati, Qatar | series/x_*.csv, xv_*.csv (volumi) | dal 1996–2015 |
| Settori e industrie | 11 settori, biotech, costruttori, vendita al dettaglio, minerarie, petrolio, banche, assicurazioni, immobiliare, semiconduttori, software, cloud, sicurezza, trasporti, difesa, energia pulita, uranio, litio, robot | idem | idem |
| Stili e fattori | grandi/piccole aziende, crescita/valore, momento, qualità, bassa volatilità, alto beta, pesi uguali, dividendi | idem | idem |
| Obbligazioni e credito | titoli di Stato a ogni durata, aziende investment grade e high yield, prestiti, mercati emergenti, municipali, indicizzati all'inflazione, ipotecari, tesoreria, leve su obbligazioni, rendimenti ^TNX ^FVX ^IRX ^TYX | idem | dal 1980–2007 |
| Valute | 30 cambi (dollaro contro tutte le principali), indice dollaro e ETF su dollaro, euro, yen, sterlina, franco, australiano, canadese | idem | dal 1996–2003 |
| Materie prime | petrolio WTI e Brent, gas, benzina, gasolio, oro, argento, platino, palladio, rame, mais, grano, soia, caffè, zucchero, cotone, cacao, bovini, suini, ETF e minatori | idem | dal 2000 |
| Future sugli indici e sui titoli di Stato | ES, NQ, YM, RTY, 2, 5, 10 e 30 anni | idem | dal 2000 |
| Criptovalute | Bitcoin, Ethereum, Solana, BNB, XRP, ADA, DOGE, AVAX, LINK; ETF Bitcoin/Ethereum; Coinbase, MicroStrategy, minatori | idem | dal 2014–2021 |
| Banche estere | Deutsche Bank, UBS, Barclays, Santander, ING, BBVA, HSBC, NatWest, Lloyds, Itaú, Banco Macro, TD, RBC, Scotiabank | idem | dal 1990–2000 |
| ETF a leva e volatilità | VXX, UVXY, SVXY, VIXY, SQQQ, TQQQ, SH, SDS, SPXU, SPXL, TZA, TNA, UPRO, TMV, TMF | idem | dal 2009 |
| FRED | circa 230 serie: tutte le scadenze dei titoli di Stato, inflazione attesa, tassi interbancari, SOFR, spread di credito per rating, bilancio della Fed, prestiti e depositi delle banche, standard di prestito, condizioni finanziarie (componenti), volatilità e incertezza, lavoro, inflazione, redditi e consumi, produzione, case, commercio, debito, cambi, tassi esteri, materie prime, indici di Borsa | series/f_*.csv | dalla prima data disponibile |
| Put/call CBOE | totale, azioni, indici, S&P 500, VIX, ETF | series/cboe_pc_*.csv | storici dove disponibili, poi ogni giorno |
| Barre a 5 minuti | 52 strumenti: indici, volatilità, ETF principali, settori, future, obbligazioni, cambi, oro, petrolio, Bitcoin | intraday/AAAA-MM/*.csv.gz | da oggi (Yahoo dà solo 5 giorni: per questo si salva ogni giorno) |
| S&P 500 titolo per titolo | chiusure e volumi di tutte le aziende dell'indice | componenti/close_*.csv.gz, vol_*.csv.gz, elenco.csv (settore) | dal 2015, ogni giorno. Attenzione: sono le aziende di OGGI (chi è uscito dall'indice manca) |
| Catene di opzioni | per ogni scadenza di SPY, QQQ, IWM, TLT, HYG, GLD, USO, XLF, S&P 500 e VIX: volumi e posizioni aperte call/put, rapporto put/call, volatilità al centro, asimmetria (put 25 delta meno call 25 delta), gamma netta | opzioni_ext/AAAA-MM.csv | da oggi (non ricostruibile dopo) |
| Già archiviati prima | catena completa delle opzioni SPY (archive/), VIX e curva, MOVE, SKEW, put/call, margin debt, Fear & Greed, bilanci aziende, revisioni degli utili | data/ | vedi Archivio dati |

## Note
- I dati sono grezzi: nessun giudizio, nessuna regola. Servono per ricerche con protocollo scritto in anticipo.
- Le chiusure dei giorni in corso di future, valute e criptovalute si salvano dal giorno dopo (la barra del giorno è parziale).
- Volumi giornalieri: dal 2015 per i titoli quotati.
- Spazio: circa 25–30 MB di storia caricata una volta, poi circa 15 MB all'anno (le barre a 5 minuti sono divise per mese e compresse per non appesantire il repository).
- Per aggiungere un'altra fonte: `src/armor/accumulo.py` (elenchi YAHOO, FRED_EXT, OPZIONI, INTRADAY).
