---
title: "Armor: report completo su cosa fa e come lo fa"
subtitle: "Stato al 24 novembre 2026 (aggiorna il report tecnico dell'8 novembre)"
---

# 1. In breve

Armor è un'app personale che ti dice **quanto è delicato il mercato** per chi investe ogni mese su VWCE (il fondo azionario mondiale), con un obiettivo preciso: capire quando conviene fare entrate extra e quando basta il versamento normale. Non dà consigli di acquisto o vendita e non è consulenza finanziaria.

Ogni giorno scarica dati gratuiti (prezzi, paura del mercato, credito, economia, grandi fondi, notizie), li trasforma in indici da 1 a 100, calcola probabilità di calo, e salva tutto in un registro che non si può riscrivere. Il risultato è un sito che si installa come app sul telefono.

**La cosa più importante da sapere è come sono fatte le prove.** Quasi ogni idea è stata scritta in un protocollo *prima* di guardare i risultati, scelta sugli anni passati (di solito fino al 2014) e verificata sugli anni successivi, confrontata con quello che il caso produce quando si prova molte volte e si tiene la migliore. L'esito viene scritto anche quando è negativo. Per questo l'app è piena di indici «descrittivi» e povera di previsioni: pochissime cose hanno superato la prova.

**Verdetto onesto, in cinque righe:**

- Gli indici misurano bene **quanto è tesa la situazione adesso**, ma non indovinano il *quando* dei crolli.
- L'unica previsione che ha superato la prova severa è a **una settimana** (Indice crollo, media di 5 sedute), e solo di poco sopra il caso.
- Una cosa ha retto in tutti i test: quando **nessun segnale è acceso e l'indice è fermo** i cali sono quasi la metà del normale. È un fatto sul *clima*, non un segnale di acquisto o vendita.
- Regole che usano gli indici per **vendere** o per **tenere soldi da parte** (con costi e tasse) hanno sempre reso meno del semplice piano di accumulo.
- Le idee nate guardando il grafico degli ultimi 5 anni (salita lenta verso 40, indice che sale col mercato) non reggono nella storia lunga.

# 2. Come è fatta l'app

## 2.1 Struttura

Il codice è in Python (circa 40.000 righe, oltre 150 moduli) nel repository GitHub «armor». Tutti i calcoli girano su GitHub Actions, gratis. Il risultato è un sito statico su GitHub Pages, installabile sul telefono, con un servizio gratuito su Cloudflare per la sentinella dei cali improvvisi e notifiche sul telefono con ntfy. Non si usa nessuna intelligenza artificiale a pagamento: solo librerie statistiche standard (pandas, numpy, scikit-learn, scipy) e fonti gratuite.

## 2.2 Quando gira

| Flusso | Quando | Cosa fa |
|---|---|---|
| Aggiornamento giornaliero | ogni sera dopo la chiusura di Wall Street (+ riserva al mattino) | scarica i dati, calcola tutti gli indici e le previsioni, scrive il registro |
| Sito | ogni 15 minuti in orario di mercato | prezzi quasi in tempo reale e ricostruzione della pagina |
| Prossime ore | ogni 15 minuti | previsione a 1-12 ore del VWCE dai futures |
| Notizie e analisi | 4 volte al giorno nei giorni feriali | notizie, tono, analisi |
| Allarmi personali | ogni 15 minuti | notifiche sul telefono sulle soglie che scegli tu |
| Accumulo dati | sera e mattina | archivio per le ricerche future (sezione 6) |
| Grandi fondi, Opportunità, Titoli, Economia, Mercati | giornalieri o settimanali | schede dedicate |
| Convalida mensile e Ricerca modello | 1° e 3 del mese | ripetono le prove sui modelli con le stesse regole |

Dal telefono il tasto «Aggiorna dati» avvia i flussi subito.

## 2.3 Da dove vengono i dati

Yahoo Finance (prezzi, paura del mercato VIX e derivati, settori, materie prime, cambi, fondi), FRED della Fed (credito, tassi, lavoro, inflazione, liquidità), Shiller e multpl (valutazioni dal 1871), CFTC (posizioni dei grandi operatori sui futures), SEC (bilanci, operazioni dei fondi), BCE, il sondaggio AAII, notizie da feed pubblici, e un archivio proprio che si accumula giorno per giorno (opzioni, intraday a 5 minuti, componenti dell'S&P 500). Ogni fonte è indipendente: se una si rompe, le altre continuano e la pagina «Stato dell'app» lo dice.

**Regola base contro gli imbrogli:** ogni valore alla data *t* usa solo ciò che era noto a *t*, con i ritardi di pubblicazione reali (per esempio utili 150 giorni, inflazione 45, sussidi 6). Il passato non viene mai riempito con dati del futuro.

## 2.4 Le pagine

Sette sezioni: **Oggi** (Quadro di oggi, Terreno, Allerta, prezzi, notizie), **Mercati** (classifiche, Saldi, Opportunità, aziende), **Previsioni** (probabilità, modelli, minimi, segnali di fondo), **Rischio** (indici, regime, stress test, grandi fondi, valutazioni, macro), **Calendario**, **Grafici** (confronto fra indici e mercati, storico, archivio dati), **Piano** (simulatore del tuo piano di accumulo, allarmi, verifiche, stato dell'app).

# 3. Gli indici e come si calcolano

## 3.1 Indice Armor (1-100)

È il numero principale. Nasce dal motore **Titan**, che guarda il mercato da quattro «orologi» e li combina:

1. **Orologio dei prezzi**: quanto è teso l'andamento (calo dal massimo dell'anno, prezzo sotto la media a 200 giorni, volatilità recente, peggior giorno del mese).
2. **Orologio strutturale**: se il terreno sotto è fragile (credito che peggiora, liquidità della Fed che si ritira, rame contro oro, dollaro, spostamenti insoliti fra settori, inflazione e petrolio).
3. **Orologio dei minimi**: se siamo in un calo profondo ma «stabile», che di solito è vicino a un rimbalzo.
4. **Orologio dei massimi**: se i prezzi sono vicini ai massimi con tassi in salita e valutazioni alte.

Ogni misura viene prima trasformata in uno **z-score** (quanto è lontana dalla sua media degli ultimi 5 anni, limitato fra −3,5 e +3,5). Poi: un punteggio «veloce» (paura, liquidità, rimbalzo) pesa il 30%, uno «lento» (stress, ciclo, valutazioni) il 70%; il risultato diventa l'indice con una trasformazione lineare (40,5 + (rischio − 48) × 0,65), limitato fra 1 e 100.

**Scala tarata.** Per chi legge, l'indice è stato spostato in modo monotono (non cambia l'ordine dei giorni) in modo che 40, 60 e 80 corrispondano alle stesse soglie del Super Armor, ricavate dai percenti delle sole crisi finanziarie dal 1986.

**Zone (su tutta la storia 1995-2026, S&P 500):**

| Zona | Quota di giorni | Calo di almeno 10% nei 3 mesi dopo | Calo peggiore medio |
|---|---|---|---|
| Tranquillo (sotto 40) | 55% | 6% | −3,6% |
| In difficoltà (40-60) | 35% | 24% | −6,1% |
| In pericolo (60-80) | 8% | 34% | −8,8% |
| Rischio di crollo (sopra 80) | 1% | 41% | −12,1% |

La frequenza media in tutta la storia è del 15%. Il valore in sé non è una probabilità: è un punteggio di tensione relativo.

## 3.2 Super Armor (1-100)

Media di **sei pilastri**, ognuno da 1 (sano) a 100 (pericoloso), con una correzione per i minimi profondi:

| Pilastro | Cosa misura |
|---|---|
| 1 Prezzi | calo dal massimo, prezzo sotto le medie, valutazioni troppo alte |
| 2 Struttura | credito, orologio strutturale, orologio dei massimi |
| 3 Paura e opzioni | VIX, sua curva a 4 punti, volatilità dei titoli di Stato, assicurazioni sul ribasso, salti della paura |
| 4 Rotture interne | debolezza dei bond rischiosi, spostamenti fra settori, uscita degli istituzionali, leva in calo, euforia |
| 5 Economia reale | sussidi di disoccupazione, credito, permessi edilizi, recessione |
| 6 Liquidità e globale | liquidità netta, rame/oro e dollaro, mercati del mondo in sintonia |

La media dei sei viene ridotta di 9 × (quanto siamo in un minimo profondo e stabile) × (1 − rischio recessione), perché nei minimi profondi l'indice grezzo sovrastima il pericolo. Fasce: 1-25 sano, 25-40 tranquillo, 40-55 attenzione, 55-70 teso, 70-100 pericoloso.

Sotto i sei pilastri del Super Armor l'app mostra anche i cinque pilastri dell'Indice Armor (paura, liquidità, rimbalzo, stress statico, ciclo), e un **settimo riquadro «Fondi (difensività)»** senza peso: la prova ha mostrato che peggiora l'indice fino al 2014 e migliora dopo, quindi non è entrato.

Esiste anche una versione precedente (Patch 64, cinque pilastri con pesi 30/25/25/20/0: previsione, Indice Armor, economia, paura e opzioni, grandi fondi) che resta in alcune pagine.

## 3.3 Indice crollo (1-100)

Un termometro dello stress, calcolato su **12 famiglie**, ognuna trasformata in percentile sulla storia crescente (solo passato). Il modello scelto (M2) usa pesi fissati prima dei risultati:

- paura del mercato (30%), paura a breve contro tre mesi (30%), prezzo sotto le sue medie (25%), distanza dal massimo dell'anno (25%), costo del debito delle aziende (15%), fuga dai settori rischiosi (15%), scosse sui tassi (15%).

Il punteggio diventa un numero con una scala a tratti calibrata sui percentili dal 1990. Fasce: sotto 35 verde, 35-40 grigio, 40-60 giallo (mercato teso), 60-80 rosso, sopra 80 viola (panico).

**Cosa ha dimostrato.** Etichetta pre-registrata: «Non coerente»: la fascia viola non ha superato il test (pochissimi giorni). Nella gara fra 81 candidati (3 indici × 9 modi di misurarli × 3 orizzonti), scelta fino al 2014 e verifica dal 2015 sulle sole crisi finanziarie, **un solo candidato è stato promosso: la media di 5 sedute dell'Indice crollo a una settimana** (area sotto la curva 0,7493 contro 0,7460 che la migliore di 81 raggiunge per caso: indizio stretto). Nel quinto più alto il calo del 3% in 5 sedute è arrivato nel 18% dei casi contro il 6,7% normale. A un mese e a tre mesi il vincitore della scelta crolla nella verifica (0,74-0,81 → 0,54): non promosso.

Da questo deriva la riga del Quadro: «Settimana a rischio sopra la norma» quando la media a 5 sedute supera 60.

## 3.4 Sick Index: Bolla e Credito (0-100)

Due numeri che dicono se il mercato è «malato» da dentro. Derivano da **sette meccanismi** che in passato hanno innescato crolli nati nel sistema finanziario (non shock esterni): concentrazione sui pochi titoli grandi, prezzi da bolla, leva e affollamento, credito e banche, titoli di Stato che drenano le azioni, stress europeo, dollaro forte. Ogni meccanismo è un percentile della media dei suoi indicatori; «caldo» sopra 0,80.

- **Indice Bolla** = percentile della media di prezzi da bolla (valutazioni, salita a 3 anni) e concentrazione.
- **Indice Credito** = percentile della media di credito/banche e stress europeo.

Sopra 80 (zona rossa) l'app mostra cosa è successo dopo in situazioni simili (le 300 giornate più vicine per livello e variazione a 63 sedute): la salita e il calo massimi a 1 settimana, 2 settimane, 1 mese, 3 mesi.

**Esito delle prove:** nessuno dei meccanismi ha superato la prova rigorosa; per tipo di crisi, **Credito «riconosce»** (4 picchi su 4 ma pochi episodi, tipi assegnati a posteriori), **Bolla è un indizio**, Leva e Dollaro non sono supportati. Perciò sono mostrati come informazione, **non come avviso**, e hanno peso zero.

## 3.5 Terreno e Laboratorio vivo (nuovi di oggi)

Il **semaforo «Terreno»** in cima al Quadro: verde (nessun segnale acceso e indice fermo o in calo: in passato un calo dell'8% in tre mesi è arrivato circa 11-14 volte su 100 contro 19-23 negli altri giorni), neutro, rosso (Bolla o Credito sopra 80). Non dice mai di vendere.

Il **Laboratorio vivo** registra ogni giorno dal 24/11/2026 sei ipotesi con soglie già fissate (salto rapido dell'indice, indice in salita col mercato alto, terreno calmo, Bolla rossa, Credito rosso, fondi molto difensivi). Quando ci sono almeno 126 giorni valutabili e 6 episodi indipendenti, l'app scrive da sola «confermata», «smentita» o «non conclusiva». Oggi tutte dicono «in attesa».

## 3.6 Altri indici e termometri

- **Indice Occasione (0-100)**: riconosce i minimi *mentre si formano*. Due parti: **Panico** (caduta dal massimo, paura, paura a breve più alta di quella a tre mesi, credito che peggiora, prezzo sotto la media lunga) e **Svolta** (paura che rientra, curva della paura normale, credito che smette di peggiorare, prezzo che risale dal minimo, settori che risalgono). Occasione = il minore fra il panico più alto degli ultimi 63 giorni e la svolta. Stati: nessun panico, in osservazione, **coltello che cade** (panico e nessuna svolta: conveniva aspettare), occasione (sopra 50), occasione forte (sopra 70).
- **Radar dei minimi**: probabilità che nelle prossime 1 settimana, 1 mese, 3 mesi, 1 anno il prezzo *non* scenda più di una soglia; è verificato sul passato e l'etichetta dice se tiene («verificata», «parziale», «non verificata»).
- **Lungo periodo**: rendimento atteso a 2, 3, 5, 8, 10, 15 anni da una regressione sul logaritmo del CAPE (valutazioni), imparata solo su finestre già concluse.
- **Regime di mercato**: calma, tensione o crisi, tre gruppi trovati da un modello a miscela gaussiana su volatilità, distanza dai massimi e andamento a 3 mesi dal 1928. Descrittivo.
- **Rischio ciclico a 6-12 mesi**: 13 segnali classici a soglia fissa e i mesi del passato più simili a oggi. Descrittivo: nessun modello a 6-12 mesi ha superato la prova.
- **Predisposizione al crollo**: media dei percentili di dieci fattori di fragilità; non ha superato la regola, quindi non cambia l'Indice crollo.
- **Terreno lento e ribassi lenti**: pressioni su credito, famiglie, rendimenti alternativi, flussi, imprese; due chiavi per riconoscere i ribassi che durano mesi.
- **Difensività dei grandi fondi**: quanto i grandi gestori accumulano liquidità, oro o obbligazioni (fondi monetari, oro contro azioni, titoli lunghi, posizioni sui futures, protezioni dichiarate). Peso zero: nella storia non ha anticipato i crolli.

# 4. Previsioni

## 4.1 Probabilità di calo

L'app stima la probabilità che l'S&P 500 (che ha storia dal 1928, il VWCE si muove in modo molto simile) scenda oltre una soglia entro un orizzonte: 10 giorni (5%), 1 mese (5% e 10%), 3 mesi (10% e 15%), 6 mesi (10% e 20%).

- **A1**: regressione logistica su otto variabili di prezzo (volatilità a 21 e 63 giorni, il suo rapporto con quella annuale, distanza dal massimo, prezzo contro media a 200 giorni, medie a 50 e 200, rendimento a 63 sedute, peggior giorno del mese), allenata ogni giorno solo sugli esiti già noti.
- **FHS+VIX** (il motore principale a 1 e 3 mesi): volatilità GJR-GARCH con errori t di Student, stimata dal 1950, poi 5.000 percorsi simulati ricampionando gli shock storici. La varianza del primo giorno viene spostata a metà strada verso quella implicita del VIX. La probabilità è la quota di percorsi che toccano la soglia.
- **Titan+**: parte da FHS+VIX e lo corregge con i sei pilastri; i pesi si ricalcolano ogni settimana con una regressione con memoria che sbiadisce. Gira in ombra.
- **Combinazione e taratura** (ensemble, taratura annidata): pesi non negativi per orizzonte, regressione isotonica, intervalli conformali; coerenza fra orizzonti (la probabilità a 6 mesi non può essere minore di quella a 3).

**Chi vince:** la convalida mensile confronta i motori con la stessa regola. Uno sfidante sostituisce A1 solo se ha un punteggio di Brier migliore di almeno 0,005 sia nel 2000-2012 sia dal 2013 e un'area sotto la curva non peggiore di oltre 0,01. Ogni giorno la **classifica dei modelli** dà un voto da 1 a 100 (50 = «succede quello che succede di solito») e la pagina «Chi ha sbagliato di meno» mette in fila previsione, realtà e scarto di ogni modello.

## 4.2 Rendimenti e direzione

La **fascia di rendimento** è calibrata: quantili storici di un rendimento rapportato alla volatilità implicita, quindi asimmetrica (i cali sono più ampi dei rialzi). La «probabilità di rialzo» è la frequenza storica (circa 60% a un mese, 65% a tre), **non una previsione**: nessun modello provato ha previsto la direzione meglio della frequenza storica.

## 4.3 Prossime ore e Allerta

- **Prossime ore**: il VWCE chiude alle 17:30 ma Wall Street continua. Il «valore equo» si ricava dai futures sull'S&P 500 e dal cambio euro/dollaro; spiega l'86% del salto all'apertura (stimato su 570 notti 2024-2026, 86% anche su dati non usati per tarare). Non prevede la direzione di una sorpresa.
- **Allerta cali improvvisi**: due segnali, un calo forte dei futures e un salto della paura; un terreno «fragile» se il prezzo ha rotto da poco la media a 200 giorni o la paura sale in fretta. In passato il segnale migliore raddoppia la probabilità di un calo da 1,2% il giorno dopo (da 1 su 11 a 1 su 5): serve a non essere colti di sorpresa, non a indovinare il giorno. Non è un consiglio di vendere.

# 5. Altre funzioni

- **Mercati, Saldi, Opportunità, Aziende**: classifiche per periodo, i 100 titoli e fondi scesi di più con punteggio «Salute» e causa del calo, le 30 aziende con il Potenziale più alto (imbuto a canali, bilanci SEC), salute dei bilanci delle prime 30 aziende del VWCE.
- **Grandi fondi**: chi sono, cosa hanno fatto nell'ultimo trimestre (13F della SEC), strategia, notizie. Peso zero nei modelli.
- **Economia nel mondo, Segnali di fondo, Stress test**: inflazione, lavoro, crescita in tempo reale (GDPNow), flussi e posizionamento, perdite attese nelle crisi storiche in euro.
- **Il mio piano**: simulatore del piano di accumulo (i tuoi dati restano nel browser), serie di VWCE in euro con segmenti dichiarati, rischio di cambio.
- **Calendario ed eventi**: Fed, inflazione, lavoro, scadenze opzioni, trimestrali, con risultato atteso e reale.
- **Notizie**: tono con vocabolario o FinBERT, tema, per le 20 maggiori società; non entra nei modelli («pronto ma spento»).
- **Allarmi personali** sul telefono, **Stato dell'app** (dati aggiornati, diario integro), **Salute dei dati**, **Diario delle previsioni** con catena di hash (solo aggiunte, verificato alla scadenza).

# 6. Archivio per le ricerche future

Ogni giorno si salvano chiusure e volumi di centinaia di strumenti, barre a 5 minuti, riepiloghi delle catene di opzioni, componenti dell'S&P 500, serie di FRED, BCE, Tesoro, CFTC, attenzione del pubblico (Wikipedia, Google Trends), criptovalute. Nessuna di queste serie entra nei modelli: servono a cercare correlazioni fra qualche mese, con la regola «scelta sul passato, verifica in avanti». Un modulo di indicatori derivati prepara misure pronte per non ripartire da 500 colonne.

# 7. Tutte le prove, in sintesi

## 7.1 Prove sui modelli (fino all'8 novembre)

Nessun modello a 6-12 mesi ha superato la prova finale 2019-2026 (che si fa una volta sola). Modelli con tanti dati macro (MV-logit, alberi, famiglie combinate) hanno dato risultati *peggiori* della frequenza storica fuori campione. La direzione non è prevedibile. Scoperto e corretto uno sguardo al futuro negli utili (ritardo portato a 150 giorni).

## 7.2 Prove delle ultime settimane

| Idea | Esito | Numeri chiave |
|---|---|---|
| Territori di rischio endogeno | non dimostrati | per tipo: Credito «riconosce», Bolla indizio, Leva e Dollaro no |
| Difensività dei grandi fondi | non supportata | non anticipa; come 7° pilastro peggiora fino al 2014 |
| Anticipo (predisposizione) | non adottata | non supera la regola |
| Salita lenta verso 40 dell'Indice Armor (idea tua) | **non supportata, segno opposto** | dopo la salita l'indice supera 60 nell'11% dei casi contro il 18% normale |
| Indice che sale col mercato alto (idea tua) | non supportata; sensibilità alta, precisione bassa | 7 picchi su 9 catturati (p 0,002) ma dopo il segnale il calo non è più frequente |
| Salto rapido dell'indice | indizio debole | segno positivo in 6/6, ma intervalli includono 0; effetto 1-8 punti |
| Convergenza di più segnali deboli | non supportata | con 2+ segnali nel 2005-2020 il calo dell'8% è arrivato 0% delle volte (base 17%) |
| Regola di esposizione su VWCE, con tasse | **non supportata** | verifica 2013-26: 3,09× contro 4,02× del «compra e tieni» |
| Versamenti più grandi dopo i ribassi, con riserva | **non supportata** | 0,87× del piano normale; descrittivamente vero dal 2005, falso nel 1990-2004 |

**Il filo che lega i risultati.** Quando si guarda il passato, il periodo più lungo e i due blocchi (1990-2004 e 2005-2020) quasi mai concordano su un segnale d'allarme. L'unica lettura che regge sempre è il contrario: **assenza di segnali e indice fermo = meno cali**. Il piano di accumulo classico (versare sempre, subito) resta la regola da battere e finora nessuna regola costruita sugli indici ci è riuscita dopo costi e tasse.

# 8. Limiti noti

- **Pochi eventi indipendenti**: dal 2000 ci sono 6-7 grandi cali, dal 1960 una ventina. Le finestre si sovrappongono, quindi i casi davvero indipendenti sono molto meno dei giorni testati.
- **Scelte a posteriori**: pesi e soglie degli indici sono stati fissati nel 2026 guardando la storia (la taratura 40/60/80 è fatta su tutta la storia). Solo il 2024-2026 è davvero fuori campione per l'Indice Armor.
- **Dati rivisti**: i dati macro di FRED sono nella versione attuale, non in quella pubblicata allora (si applicano ritardi prudenti ma non le versioni d'epoca).
- **Base S&P 500**: il VWCE ha storia reale solo dal 2019; la parte non americana (circa il 35%) non è modellata a parte. Per le regole di investimento il VWCE è stato sostituito dall'S&P 500 senza dividendi e con liquidità a rendimento zero, un trattamento prudente per la strategia che si prova.
- **Fonti ancora da verificare**: alcune fonti (per esempio i fondi monetari della Fed, fermi al 5 ottobre) sono ferme alla fonte; il sondaggio AAII risponde con errore 403 dai server.
- **Tutti gli indici sono informativi**: nessuno ha peso nei modelli finché non supera la prova; il Laboratorio vivo dirà fra circa sei mesi quali ipotesi si confermano.

# 9. Cosa farei adesso

1. **Tenere come regola il piano di accumulo**, usando gli indici per capire il clima e non per decidere quanto stare investiti.
2. **Lasciar lavorare il Laboratorio vivo** e leggerne i verdetti fra sei mesi: è il modo giusto di far morire le ipotesi deboli o confermare quelle buone.
3. **Studiare la durata dei ribassi**: il vero punto che ha rovesciato l'idea «versa nei ribassi» è che i ribassi brevi risalgono e quelli lunghi (2000-2002) no. Un indicatore che dicesse in tempo «questo ribasso sarà lungo» varrebbe più di qualsiasi allarme.
4. **Rilanciare le azioni su GitHub** (aggiornamento giornaliero, sito, accumulo dati) per far partire il registro del Laboratorio.
