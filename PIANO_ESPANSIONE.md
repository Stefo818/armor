# PIANO_ESPANSIONE — istruzioni per Sonnet (Patch 40 → 47)

Documento scritto da Opus il 09/11/2026 su richiesta dell'utente. Contiene **tutte** le richieste dell'utente del 09/11/2026, tradotte in specifiche tecniche, algoritmi e criteri di verifica.
Si esegue **una patch per volta**, nell'ordine indicato. Ogni patch si consegna e si ferma: l'utente prova e dice «prosegui».
Se una richiesta non è realizzabile con dati gratuiti, si realizza la versione migliore possibile e lo si dice chiaramente: mai inventare dati, mai far sembrare certa una previsione.

---

## 0. Regole generali (valgono per tutte le patch)

**0.1 Vincoli del progetto (invariati).** Tutto il calcolo gira in GitHub Actions; nessuna AI a pagamento; app in italiano; «non è una consulenza finanziaria». Non toccare A1, FHS, FHS+VIX/V1T1, i protocolli già registrati (PROTOCOLLO_VERIFICA.md, PROTOCOLLO_VRP.md), adozione.json, verifica_storica.json. Test sempre verdi (`python3 -m pytest -q`), ruff pulito sui file nuovi o modificati, compilazione con python3.11 (`python3.11 -m compileall -q src`: niente backslash o virgolette annidate dentro le espressioni delle f-string).

**0.2 Onestà dei numeri.** Ogni punteggio o previsione mostrata deve avere accanto la sua **affidabilità misurata** (quante volte, nel passato o nelle settimane già verificate, la fascia ha avuto ragione). Le parole «sicuro», «certo», «garantito» non compaiono mai nell'app: si usa «stimato», «storicamente», «nel X% dei casi». Le scale chieste dall'utente (1–100) si mantengono, ma l'etichetta descrive cosa misurano davvero.

**0.3 Sincronizzazione con il PC (fare all'inizio di ogni patch).** Il repository vero è `D:\Armor` sul PC; la copia di lavoro è `/home/claude/armor_work/Armor`. Prima di modificare un file, confronta lo sha1 tra PC (device_bash: `sha1sum`) e copia cloud; se diverso, ristagia dal PC solo quel file. Nota: `web/sw.js` sul PC era più avanti della copia cloud: la cache attuale è `armor-v39`; ogni patch la incrementa di 1.

**0.4 Risparmio token.** Leggi solo le parti di file che servono (grep + sed per righe). Raggruppa i controlli in **un solo script** in scratchpad eseguito una volta. Massimo due screenshot per patch (430 px e 1000 px) e solo delle parti cambiate. Riusa i moduli esistenti: `store`, `sources` (`_get`, `pausa`, `upsert`, `set_status`), `traduzione.py`, `finbert.py`, `news.py`, `guard.run_parallel`, `archive.py`, `valuations.py`, `holdings.py`, `aziende.py`, `mappa.py`, `confronto.py`, `cruscotto.py`, `report.py` (`_safe`, pagine caricate a richiesta).

**0.5 Dati grandi.** Non committare file pesanti a ogni giro (la storia git esploderebbe). Per l'universo di titoli usa `actions/cache` o un ramo orfano `dati-grandi` sovrascritto (force-push, una sola commit). Nel ramo principale vanno solo i risultati compatti (JSON delle liste, max qualche centinaio di KB per pagina) e i registri delle previsioni (CSV piccoli, necessari per lo storico).

**0.6 Consegna (identica per ogni patch).** zip con **solo** i file cambiati → `/mnt/user-data/outputs/patchNN.zip` → SendUserFile → `device_commit_files` su `D:\Armor\patchNN.zip` → estrazione sul PC con device_bash (`python3 -c "import zipfile;zipfile.ZipFile('patchNN.zip').extractall('.')"`) → aggiorna `CONTINUA_DA_QUI.md` (sezione «PATCH NN») → risposta all'utente in italiano, breve, con blocchi **[PowerShell]** (comandi completi: `cd D:\Armor`, `python -m pytest -q`, `git add -A`, `git commit -m "..."`, `git push`), **[Chrome]** (cosa aprire e lanciare su GitHub Actions, cosa controllare), **[Telefono]** (cosa provare nell'app). Elenca sempre cosa non è stato possibile verificare.

**0.7 Interfaccia.** Prima il telefono (430 px), poi desktop. Stile coerente con l'app (variabili CSS `--card`, `--bd`, `--tx`, `--mu`, `--ac`, `--ok`, `--warn`, `--bad`; tema scuro e chiaro). Componente unico per le descrizioni: **`window.armorInfo`** (da creare nella Patch 40, in un modulo `infobox.py` con JS+CSS), usato ovunque:
- su desktop si apre al passaggio del mouse (ritardo 250 ms);
- su touch si apre con la pressione lunga (450 ms) oppure toccando l'icona «ⓘ»;
- si chiude toccando fuori o con la ×;
- non deve mai bloccare il tocco normale (accendi/spegni);
- i testi stanno in un dizionario Python `GLOSSARIO_SERIE` (nuovo file `glossario_serie.py`), riusato anche dalla pagina Glossario.

---

## PATCH 40 — Grafico «Indice Armor contro i mercati» (confronto.py)

**40.1 Togli il bagliore dalle linee.** In `line()` elimina `shadowColor/shadowBlur`. Il bagliore resta **solo** sulle icone dei pulsanti attivi (già fatto in Patch 39: bordo colorato + `box-shadow` sul pallino). Aggiorna il testo esplicativo sopra il grafico: oggi dice «giallo tratteggiato / blu tratteggiato», diventa «linee continue».

**40.2 Stato della finestra.** Sostituisci `per` + `zoom` con un'unica vista `view=[i0,i1]`:
- i pulsanti Periodo impostano `view=[n-N, n-1]`;
- lo zoom per selezione (Patch 39) imposta `view=[a,b]`;
- lo scorrimento sposta `view` mantenendo la larghezza, bloccato ai bordi dei dati;
- la barra «Zoom: … · Azzera» compare quando `view` non coincide con un Periodo.

**40.3 Scorrimento avanti/indietro.**
- **Mouse, tasto destro.** Su `contextmenu` del canvas `preventDefault`. `mousedown` con `button===2` attiva lo scorrimento: spostamento in pixel `dx` → indici = `round(dx*(i1-i0)/(W-L-R))`, verso naturale (trascini a destra = vai indietro nel tempo). Cursore `grabbing`.
- **Touch, due dita.** Con 2 tocchi la finestra si sposta col punto medio; allargando o stringendo le dita si zooma attorno al punto medio (minimo 20 sedute). Il canvas tiene `touch-action: pan-y`, che lascia la pagina scorrere in verticale con un dito e consegna i gesti a due dita al JS.
- **Tasti e pulsanti.** Tasti ← → quando il grafico ha il focus (`tabindex=0`). Pulsanti piccoli «◀ ▶» ai lati della barra zoom, utili su telefono.
- Un dito in orizzontale resta la **selezione per lo zoom** (Patch 39). Un tocco singolo apre il riquadro valori.

**40.4 Più serie, entrambe le aree accendibili.** Nuovo elenco `SERIES` con un campo `pannello` («alto»: prezzi in base 100; «basso»: indicatori) e un campo `gruppo` per raggruppare i pulsanti. Anche S&P 500 e VWCE diventano pulsanti accendibili (accesi di default). I pulsanti dell'area bassa sono raggruppati per categoria; ogni gruppo ha un titolo e si apre o chiude per non riempire lo schermo. Di default restano aperti solo «Rischio Armor» e i gruppi con almeno una linea accesa.

Area alta, base 100 dal primo giorno della finestra in cui la serie esiste. La legenda va presa dai pulsanti accesi; sparisce quella fissa.

| chiave | nome | fonte (Yahoo salvo diverso) | note |
|---|---|---|---|
| sp500 | S&P 500 | esistente | |
| vwce | VWCE | `vwce_display()` (L&S) | |
| nasdaq100 | Nasdaq 100 | esistente `^NDX` | |
| mweq | MSCI World Equal Weight (Invesco, MWEQ) | **verifica** `MWEQ.DE` (Xetra; ISIN IE000OEF25S1); alternative `MWEQ.L`, `MWEQ.MI` | quotato dal 2023: storia corta, dirlo nel riquadro |
| rsp | S&P 500 Equal Weight | esistente `RSP` | storia lunga, utile accanto a MWEQ |
| msci_world | MSCI World | nuovo `URTH` | |
| stoxx600 | Europa (STOXX 600) | nuovo `^STOXX` | |
| eem | Mercati emergenti | esistente `EEM` | |
| dax, ftsemib, nikkei | DAX, FTSE MIB, Nikkei | esistenti | |
| iwm | Small cap USA (Russell 2000) | esistente `IWM` | |

Area bassa. Le scale restano quelle attuali: scala reale con una sola linea, 0–100% del min–max con più linee.
- **Rischio Armor.** Indice Armor, le 4 probabilità, le 8 famiglie (oggi ce ne sono solo 3: aggiungi le altre 5 da `aix["G"]`), il «Regime di tensione» (dopo la Patch 43).
- **Volatilità.** VIX, VIX/VIX3M (struttura a termine: sopra 1 = paura immediata), VVIX, MOVE, SKEW.
- **Credito e tassi.** HY spread, IG spread, BAA-10Y, rendimento 10 anni (FRED `DGS10`), curva 10Y-3M, curva 10Y-2Y, rendimento reale 10 anni (FRED `DFII10`), NFCI.
- **Valutazioni.** P/E S&P (`pe_m`), P/S S&P (`ps_m`), CAPE, **P/E previsto** e **P/S previsto** (sotto), Buffett indicator (FRED `NCBEILQ027S` / `GDP`, trimestrale), rendimento utili meno 10Y (equity risk premium semplice).
- **Materie prime e cripto.** Bitcoin (`BTC-USD`), Ethereum (`ETH-USD`), oro, argento (`SI=F`), petrolio WTI, rame, rapporto rame/oro (tende a salire con l'economia), gas naturale (`NG=F`).
- **Sentimento e ampiezza.** Put/Call (vedi sotto), AAII rialzisti-ribassisti, % titoli sopra la media a 200 giorni (`breadth200`), dollaro (DXY), EUR/USD.
- **Mercato.** Distanza dai massimi S&P, RSP/SPY (ampiezza: scende quando salgono solo i giganti).

Dettagli da gestire:
- **Put/Call con storia lunga.** Prova la serie storica CBOE (`https://cdn.cboe.com/resources/options/volume_and_call_put_ratios/equitypc.csv`, fino a circa il 2019) unita ai dati giornalieri CBOE recenti. Se l'endpoint giornaliero non risponde, usa l'archivio SPY esistente e scrivi «storia breve» nella descrizione.
- **P/E e P/S previsti (la «capitalizzazione/fatturato futuro» dell'utente).** Nuovo job settimanale `previsti.py`. Prendi i ~500 titoli dell'S&P 500 (lista da Wikipedia, salvata in cache) con yfinance `info`: `marketCap`, `forwardEps`/`forwardPE`, e la stima ricavi «+1y» da `revenue_estimate`. Calcola la somma delle capitalizzazioni divisa per la somma degli utili attesi, poi per la somma dei ricavi attesi. Salva una riga a settimana in `data/series/pe_fwd.csv` e `ps_fwd.csv`. La storia parte da oggi: scrivi «in raccolta dal 11/2026» nella descrizione. Stesso calcolo per VWCE usando le principali partecipazioni di `holdings.py`, con la copertura in % del peso dichiarata.

**40.5 Descrizioni.** Ogni pulsante ha la sua scheda `armorInfo` (vedi 0.7) con quattro voci:
- **Cos'è**, 1–2 frasi.
- **Cosa rappresenta per chi ha VWCE.**
- **Come si legge**: soglie tipiche e valori nel 2008, 2020, 2022 presi dai dati.
- **Fonte e frequenza**, con il ritardo.

Scrivi i testi in `GLOSSARIO_SERIE` per tutte le serie.

**40.6 Prestazioni.** Il JSON del confronto cresce con le nuove serie. Arrotonda i valori e usa una frequenza adeguata: le serie mensili non si ripetono ogni giorno, ma si inviano come coppie (indice, valore) e si riempiono nel browser. Tieni `series/confronto.json` sotto ~1,5 MB.

**Verifica 40.**
- Scorrimento con tasto destro e con due dita (Playwright: `page.touchscreen` non fa il multitouch, quindi simula con `dispatchEvent` di TouchEvent con 2 touches).
- Lo zoom per selezione funziona ancora.
- Nessuna ombra nelle linee.
- Ogni pulsante ha una descrizione.
- MWEQ è presente, o c'è un messaggio chiaro se Yahoo non lo trova.

---

## PATCH 41 — Pagina «Oggi»: nuovo ordine, Semafori ridisegnati, schede delle famiglie

**41.1 Nuovo ordine della pagina «Oggi».**
1. Indice Armor (termometro + tendenza) e le 4 schede VIX, Put/Call, S&P 500, VWCE, con la riga «In tempo reale…».
2. **Semafori di oggi**, nella nuova grafica (41.2).
3. Le schede valutazione VWCE / S&P 500 / Nasdaq 100 (P/E, P/S), «Prossimo evento importante», poi il grafico «Indice Armor contro i mercati» della Patch 40.
4. Tutto il resto, nell'ordine attuale (il riquadro «Regime di tensione» della Patch 43 andrà in testa a questo blocco).

**41.2 Semafori di oggi: più espanso, bello, non invadente.** Oggi è una riga di testo con 3 link. Diventa una scheda di altezza contenuta, circa 140 px su telefono quando è chiusa:
- **Barra divisa in proporzione**, verde/gialla/rossa, con i numeri dentro («35 · 16 · 8»). Ogni parte, toccata, apre l'elenco dei semafori di quel colore (riusa `data-semlist`).
- **Una riga di 8 «pillole», una per famiglia** (Paura, Credito, Tassi, Valutazioni, Tendenza, Sentimento, Economia, Modello). Ognuna mostra il nome breve e un pallino per ogni indicatore della famiglia nel suo colore (es. ●●●○), con il colore di bordo della famiglia: rosso se ha almeno un rosso e più rossi che verdi, giallo se misto, verde se tutto verde. Al tocco si apre sotto, in linea, l'elenco degli indicatori della famiglia con valore, colore e una frase. Su telefono le pillole vanno su 2 righe.
- **Riga «Cambiati da ieri»**: gli indicatori che hanno cambiato colore rispetto al giorno prima (es. «VIX: giallo → rosso»). Serve salvare ogni giorno i colori in `data/semafori_storia.csv` (data, chiave, colore). Se non è cambiato nulla, la riga dice «Nessun cambio da ieri».
- Animazione leggera solo all'apertura (altezza), niente lampeggi.

**41.3 Schede delle intestazioni nella mappa settimanale (mappa.py, immagine 6 dell'utente).** Al passaggio del mouse o alla pressione lunga su ogni intestazione di riga si apre una scheda `armorInfo` dettagliata. Le intestazioni sono: VWCE % settimana, S&P 500 % settimana, Indice Armor, Paura e stress, Credito e liquidità, Tassi e obbligazioni, Valutazioni, Tendenza dei prezzi, Sentimento e ampiezza, Economia reale, Modello statistico, e ogni singolo indicatore quando la famiglia è aperta. Contenuto:
- **Cosa misura**, 2–3 frasi.
- **Cosa comprende**: elenco degli indicatori della famiglia con il loro peso, letti da `armor_index.GROUPS`, mai scritti a mano.
- **Come leggere i numeri**: 0–100 = posizione rispetto alla propria storia (percentile su finestra mobile + soglie), sopra 70 = stress storicamente alto; il colore della cella; perché Valutazioni è spesso a 100 per mesi (misura un livello che cambia lentamente e segnala rischio di lungo periodo, non un crollo imminente).
- **Esempi**: il valore della famiglia a fine 2007, marzo 2020, ottobre 2022 e oggi, calcolati.
- **Peso nell'Indice Armor** e ritardo dei dati.

Oggi il tocco su `.rl` seleziona la riga: aggiungi un'icona «ⓘ» a destra del nome che apre la scheda, mentre il resto della cella mantiene il comportamento attuale. La stessa scheda va usata nella pagina «Indici».

**41.4 Correzioni piccole trovate da Opus guardando gli screenshot.**
- (a) Il termometro dell'Indice Armor mostra ancora «Ieri 53 / Sett. fa 45». Rendilo coerente con la Patch 38: «Il 06/11 53 · Il 30/10 45», con le date reali delle osservazioni.
- (b) La scheda Put/Call mostra «Il 07/11» (sabato). L'archivio opzioni usa la data del giro e non quella della seduta. In `archive.archive_spy_options` usa come `date` l'ultima seduta USA chiusa (giorno feriale ≤ oggi a New York, saltando i festivi del calendario NYSE già presente in `calendario.py`) e non scrivere una riga se la seduta è già presente. Elimina dal CSV le righe con data di sabato o domenica.
- (c) Il testo sopra il grafico parla di linee tratteggiate (vedi 40.1).

---

## PATCH 42 — Notizie

**42.1 Nuova pagina «Notizie».** Raggiungibile con **un tocco**:
- voce nel menu principale;
- scheda «Notizie» nell'Assistente Armor, accanto ad «Analisi di oggi»;
- il tocco sulla barra delle notizie in basso apre questa pagina sulla notizia mostrata.

Contenuto:
- **Raggruppate per giorno**, dalla più recente: titoli «Oggi», «Ieri», poi «Venerdì 6 novembre».
- Ogni notizia mostra ora, fonte, titolo in italiano (`traduzione.applica`), sotto il titolo originale in piccolo, un'etichetta di tono (positivo/negativo/neutro da FinBERT) e un'etichetta di tema (macro, Fed, settori, aziende di VWCE, temi come robotica e farmaci). Ha il link all'originale.
- **Filtri a pulsanti**: Tutte · Macro e Fed · Mercati · Aziende di VWCE · Settori e temi · Solo negative. Più una **ricerca testuale**.
- Archivio di 30 giorni: oggi `news.run` salva `data/news/AAAA-MM-GG.json`. Genera `site/series/notizie.json` con gli ultimi 30 giorni, deduplicati per titolo normalizzato, e carica la pagina a richiesta.
- Le notizie dentro «Analisi di oggi» restano dove sono.

**42.2 Barra in basso più lenta.**
- `TICKER_JS`: intervallo da 5 s a **9 s**, con dissolvenza di 400 ms. Pausa quando il dito o il mouse è sopra la barra; riparte 3 s dopo.
- Ordine: dalla più recente alla meno recente, con prima la data breve («oggi 14:20»).
- Le notizie dei giorni precedenti compaiono solo dopo quelle di oggi.

---

## PATCH 43 — «Regime di tensione» (l'osservazione dell'utente)

**43.1 Cosa ha già trovato Opus.** Analisi del 09/11/2026: Indice Armor giornaliero dal 2000 contro S&P 500; «stabile sopra T per N sedute» = minimo mobile di N sedute ≥ T. Basi storiche nei 6 mesi successivi: chiusura negativa 29%, calo ≥10% 27%, nuovo minimo a 6 mesi 32%.

| condizione | chiusura negativa a 6 mesi | calo ≥10% entro 6 mesi | nuovo minimo a 6 mesi |
|---|---|---|---|
| ≥40 per 20 sedute | 38% | 40% | 47% |
| ≥50 per 20 sedute | 48% | 50% | 58% |
| ≥50 per 60 sedute | 52% | 57% | 59% |
| ≥45 e S&P già −10% dal massimo | 46% | 51% | 59% |
| ≥45 e S&P a meno del 5% dal massimo | 29% | 24% | 21% (nessun peggioramento) |
| Armor < 35 | 23% | 16% | 16% (segnale di calma) |

Limiti emersi:
- **L'effetto è concentrato nel 2000–2012.** Dal 2013, con ≥45 stabile, l'S&P ha reso +11,5% a 6 mesi contro +6,4% di base.
- **Gli episodi indipendenti sono solo 12.** I giorni si sovrappongono, quindi la fiducia statistica reale è bassa.
- **Oggi** l'indice è 50–51, ma 20 sedute fa era sotto 40: la condizione «stabile» non è ancora scattata.

Conclusione: l'osservazione è vera nei dati come **regime** (più probabili cali graduali e nuovi minimi, soprattutto se il mercato è già sotto i massimi), ma non è dimostrata fuori campione. Va trasformata in un indicatore misurato e verificato in modo onesto, non venduta come certezza.

**43.2 Analisi da fare (file `regime.py`, comando `python -m armor esperimento-regime`).**
1. **Prima registra il protocollo** in `PROTOCOLLO_REGIME.md`, prima di guardare i risultati 2013–2026. Contenuto:
   - le varianti (massimo 4);
   - gli esiti;
   - la metrica;
   - la regola di adozione;
   - la data.

   Annota ogni esecuzione in `data/protocollo_regime_log.csv`, come per il VRP.
2. **Varianti pre-specificate (massimo 4).**
   - (V1) minimo mobile a 20 sedute ≥ 45;
   - (V2) media mobile a 60 sedute ≥ 45;
   - (V3) **«Pressione accumulata»**: P_t = Σ_{k≥0} λ^k · max(0, A_{t−k} − 40), con λ = 0,97 (mezza vita ~23 sedute), normalizzata in 0–100 sul percentile storico espanding. Misura insieme quanto e da quanto l'indice sta sopra 40, cioè lo «stabilmente sopra» dell'utente in forma continua;
   - (V4) V3 combinata con la distanza dai massimi dell'S&P (interazione: pressione alta × mercato già sotto −5%).
3. **Esiti (orizzonte 126 sedute).**
   - (a) nuovo minimo sotto il minimo delle 126 sedute precedenti;
   - (b) calo massimo ≥10% dal giorno del segnale;
   - (c) rendimento a 126 sedute < 0;
   - (d) **«calo graduale»**: rendimento a 126 sedute ≤ −5% **e** volatilità realizzata nel periodo sotto la mediana storica (distingue la discesa lenta dal crollo).
4. **Metodo.**
   - Regressione logistica walk-forward (riaddestrata ogni anno, solo dati passati) di ogni esito sulla variante. Confronto con il modello A1 ufficiale (`p_3m`): la variante aggiunge informazione oltre A1? Misura con Brier skill score e AUC, con intervalli **block bootstrap** (blocchi di 126 sedute, 2000 ripetizioni).
   - Statistiche **per episodio**, non per giorno: inizio episodio = prima volta che la condizione scatta dopo almeno 60 sedute senza.
   - **Analisi di sopravvivenza (Kaplan-Meier)**: probabilità di toccare un nuovo minimo entro t sedute, in funzione di quanti giorni il regime dura da quando è scattato.
   - **Robustezza su altri mercati**: stessa regola, esiti su STOXX 50, Nikkei, VWCE (con la serie proxy). L'indice è costruito su dati USA, quindi questi esiti sono un test semi-indipendente.
   - Divisione: scelta della variante su 2000–2012, **una sola verifica** su 2013–oggi.
5. **Regola di adozione (da scrivere nel protocollo).** La variante migliore entra come **indicatore ufficiale** nell'app solo se su 2013–oggi:
   - il Brier skill score rispetto alla base è > 0 con intervallo al 90% sopra 0;
   - aggiunge informazione rispetto ad A1;
   - ha almeno 4 episodi.

   Altrimenti resta un **indicatore descrittivo**, con la scritta «non verificato fuori campione». In ogni caso parte un **registro in ombra** quotidiano (`data/regime_ombra.csv`) che verifica la regola sui mesi futuri.

**43.3 Interfaccia.**
- **Riquadro compatto in «Oggi»** (testa del blocco 4). Contiene:
  - lo stato con 4 livelli: Calma (<35) · Normale · Tensione in formazione (sopra 45 da meno di 20 sedute) · Tensione persistente (condizione scattata), con la variante «… con mercato già in calo» se l'S&P è sotto −5% dal massimo;
  - un contatore «da X sedute sopra 45»;
  - la barra della Pressione accumulata;
  - una frase con le probabilità storiche per lo stato attuale (es. «Storicamente, in questo stato, nuovi minimi nei 6 mesi successivi nel 58% dei casi contro il 32% normale; 12 episodi dal 2000; dal 2013 il segnale non è confermato»).
- **Pagina «Regime di tensione»** (menu) con quattro parti:
  - grafico S&P 500 (scala log) con le **fasce colorate** dei periodi di regime, cioè la visualizzazione di quello che l'utente ha notato;
  - tabella degli esiti per stato (con n giorni e n episodi);
  - elenco degli episodi passati con data, durata, calo massimo, nuovo minimo sì/no, rendimento a 6 e 12 mesi;
  - curva di sopravvivenza («probabilità di nuovo minimo entro t mesi»), più il risultato del protocollo e lo stato del registro in ombra.
- **Indicazioni pratiche per chi fa il PAC** (linguaggio prudente, non consulenza): in regime persistente con mercato in calo, storicamente i cali sono stati graduali e i prezzi più bassi sono arrivati mesi dopo. Per chi accumula ha senso **non anticipare** acquisti straordinari e distribuirli nel tempo; in regime di calma il rischio di cali ampi è stato più basso del normale. Collega questo testo al simulatore PAC esistente (`pacsim`) con un esempio storico: PAC costante contro PAC che rinvia una parte degli acquisti straordinari durante il regime, misurato sugli episodi passati.
- Aggiungi la serie «Regime» al grafico di confronto (Patch 40, gruppo Rischio Armor).

---

## PATCH 44 — «Mercati»: chi è cresciuto e chi è calato

**44.1 Contenuto.** Nuova pagina «Mercati» con:
- pulsanti periodo: 1 giorno · 1 settimana · 1 mese · 3 mesi · 6 mesi · 1 anno;
- due pulsanti grandi «▲ Cresciuti di più» / «▼ Calati di più»;
- interruttore valuta: «in euro» (default, perché l'utente investe in euro; conversione con `eurusd`) / «in valuta locale».

Categorie, ognuna con un grafico a barre orizzontali dei primi 10 e una tabella espandibile fino a 50:

| categoria | universo e fonte |
|---|---|
| Titoli | universo della Patch 45 (filtro liquidità) |
| ETF | lista curata in `data/universo/etf.csv`: ~250 ETF (UCITS su Xetra/Borsa Italiana + principali USA), con categoria |
| Settori | 11 settori GICS (SPDR XL*, già presenti) + settori Europa (ETF STOXX 600 settoriali) + temi (robotica BOTZ, AI AIQ, semiconduttori SMH, nucleare URA, difesa ITA, cybersecurity CIBR, spazio UFO, biotech XBI, energia pulita ICLN, rete elettrica GRID) |
| Cripto | top 30 per capitalizzazione: CoinGecko API gratuita (`/coins/markets`), in alternativa Yahoo `XXX-USD` |
| Materie prime | oro, argento, platino, rame, petrolio WTI e Brent, gas naturale, mais, grano, soia, caffè, cacao, zucchero, cotone, bestiame (futures Yahoo `=F`) |
| Fondi | i fondi comuni non hanno dati gratuiti affidabili: si usano gli ETF raggruppati per tipo (azionari, obbligazionari, oro, multi-asset) e si spiega in una nota |
| Aree e paesi | ~45 ETF paese MSCI (EWJ, EWG, EWQ, EWI, EWU, EWP, EWL, EWN, EWD, EDEN, ENOR, EFNL, EIRL, EWO, EWK, EPOL, TUR, EWZ, EWW, ECH, EPU, ARGT, GXG, EWC, INDA, MCHI, EWY, EWT, EWH, EWS, EWA, ENZL, EIDO, EWM, THD, EPHE, VNM, KSA, UAE, QAT, EZA, NGE/AFK, ISRA, EGPT) e continenti (VGK, AAXJ, ILF, AFK, SPY+EWC per Nord America, EWA+ENZL per Oceania) |

**44.2 Grafici.**
- **Torte, o meglio ciambelle con legenda.**
  - (a) Tra i 100 titoli cresciuti di più (o calati), quota per settore.
  - (b) Quota per area geografica.
  - (c) Nella vista generale, quante attività di ogni categoria sono salite o scese.
- **Planisfero.**
  - Libreria `d3-geo` + `topojson-client` e il file `world-atlas` 110m, **copiati nel sito** (niente CDN: la PWA deve funzionare offline).
  - Ogni paese è colorato con il rendimento del suo ETF: scala divergente rosso → grigio → verde centrata su 0, limiti simmetrici al 95° percentile del periodo. Paesi senza dato in grigio tratteggiato.
  - Al tocco su un paese: nome, ETF usato, rendimento, posizione in classifica.
  - Sopra la mappa, 6 barre per continente.
  - Su telefono la mappa è larga quanto lo schermo, con zoom a due dita.
- **Tabelle**: nome, ticker, categoria, % del periodo, prezzo, mini-grafico 30 giorni (sparkline SVG).

**44.3 Dati e aggiornamento.** Job giornaliero `mercati.yml` dopo la chiusura USA (22:30 UTC, giorni feriali), con download in blocchi `yf.download(..., auto_adjust=True, threads=True)`. Output `site/series/mercati.json`, con i rendimenti per periodo già calcolati e le sparkline ridotte a 30 punti. Rendimenti sempre su prezzi rettificati. Scarta i movimenti assurdi (> +300% o < −95% in un giorno) se non confermati da una seconda fonte.

---

## PATCH 45 — Motore titoli (base comune per Saldi e Opportunità)

**45.1 Universo «tutto il mercato, anche small cap».**
- **USA.** Elenchi ufficiali gratuiti Nasdaq Trader (`https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt`, `otherlisted.txt`, con il flag ETF e il flag test issue). In più, per la foto giornaliera dell'intero mercato in una richiesta, lo screener Nasdaq (`https://api.nasdaq.com/api/screener/stocks?tableonly=true&download=true`, non ufficiale: serve un User-Agent da browser; se Actions viene bloccato, si ripiega su yfinance). Fornisce prezzo, variazione %, capitalizzazione, settore, paese.
- **Resto del mondo.** `yfinance.screen` con `EquityQuery`, per regione (de, it, fr, gb, nl, es, ch, se, dk, no, fi, jp, kr, tw, hk, cn, in, au, ca, br, mx, za…) e capitalizzazione minima. Massimo 250 risultati per query: pagina con `offset`, una query per regione e fascia di capitalizzazione.
- **Esclusioni.** Prezzo < 1 (in valuta), capitalizzazione < 50 M$ (small cap incluse, microcap spazzatura no), controvalore medio giornaliero < 500 k$ su 20 sedute. Fuori anche SPAC, warrant, diritti, unità, privilegiate, ETF a leva o inversi (parole nel nome: 2x, 3x, Ultra, Leveraged, Inverse, Bear, Short) e titoli con raggruppamento azionario nei 30 giorni (segnalato da yfinance `splits`, o salto ≥ 5× con volume anomalo).
- Universo atteso: ~6.000–9.000 titoli.

**45.2 Prezzi.** Archivio delle chiusure rettificate degli ultimi 260 giorni per tutto l'universo, nel ramo `dati-grandi` o in cache (vedi 0.5), formato parquet. Aggiornamento giornaliero con la foto dello screener più `yf.download` a blocchi per i mancanti. Da qui si calcolano i rendimenti a 1g, 3g, 1s, 1m, 3m, 6m, 12m, la volatilità, il beta rispetto all'ETF di settore e il volume relativo.

**45.3 Fondamentali (solo sulla lista ristretta: costosi).** Il calcolo procede in due fasi:
1. **Pre-selezione economica sui prezzi.**
2. **Fondamentali** solo per i ~300–600 candidati al giorno (Saldi) o per settimana (Opportunità), con cache di 7 giorni per titolo.

Fonti:
- **USA, ufficiale e gratuita: SEC EDGAR XBRL** (`https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json`; mappa ticker→CIK in `https://www.sec.gov/files/company_tickers.json`). Ricavi trimestrali, utile, cassa, debito, azioni in circolazione, flusso di cassa operativo, capex. Contiene anche **`RevenueRemainingPerformanceObligation` (RPO), cioè i contratti già firmati non ancora fatturati**: è il dato che l'utente chiama «molti contratti già firmati». Ogni valore ha la data `filed`: usala per i test storici senza guardare il futuro.
  - La SEC richiede un User-Agent con un contatto e massimo 10 richieste al secondo. **Non inventare un'email:** leggi il segreto GitHub `SEC_USER_AGENT`, che l'utente crea (le istruzioni vanno nella risposta della patch). Senza segreto, la SEC si salta e si usa solo yfinance.
- **Tutti i mercati: yfinance.**
  - `info`: marketCap, trailingPE, forwardPE, priceToSalesTrailing12Months, enterpriseToRevenue, enterpriseToEbitda, grossMargins, operatingMargins, profitMargins, revenueGrowth, earningsGrowth, debtToEquity, currentRatio, freeCashflow, totalCash, returnOnEquity, shortPercentOfFloat, heldPercentInsiders, targetMeanPrice/Low/High, recommendationMean, numberOfAnalystOpinions, longBusinessSummary.
  - `quarterly_income_stmt`, `quarterly_balance_sheet`, `quarterly_cashflow`.
  - `revenue_estimate`, `earnings_estimate`, `eps_trend`, `eps_revisions`, `upgrades_downgrades`, `insider_transactions`/`insider_purchases`, `calendar`.
- **Contratti pubblici USA**: USAspending.gov API gratuita (`/api/v2/search/spending_by_award/` per nome del destinatario). Utile per difesa, aerospazio e tecnologia governativa: valore dei contratti assegnati negli ultimi 12 mesi rispetto al fatturato.

**45.4 Indicatori calcolati per ogni titolo (`salute.py` o nuovo `fondamentali_titoli.py`).**
- **Fatturato ultima trimestrale**, con freccia ▲/▼ rispetto allo stesso trimestre dell'anno prima (e rispetto al trimestre precedente in piccolo).
- **Rapporti di valutazione**:
  - P/S = capitalizzazione / fatturato 12 mesi;
  - P/E = capitalizzazione / utile 12 mesi;
  - **P/S previsto** = capitalizzazione / fatturato atteso a 12 mesi (stima media analisti; l'utente lo chiama «capitalizzazione/fatturato previsto con i contratti futuri»);
  - P/E previsto;
  - EV/EBITDA;
  - **Capitalizzazione / RPO** e **RPO / fatturato annuo** («anni di fatturato già firmati»), quando disponibili.
- **Salute**:
  - Piotroski F-score (0–9);
  - Altman Z (Z'' per le società non manifatturiere; non usarlo per banche e assicurazioni, per cui valgono ROE, P/B e la qualità degli utili);
  - copertura interessi;
  - debito netto / EBITDA;
  - current ratio;
  - margine lordo e tendenza;
  - margine FCF;
  - ROIC/ROE;
  - **mesi di autonomia di cassa** per chi perde soldi (cassa / consumo trimestrale × 3);
  - **diluizione**: azioni in circolazione rispetto a un anno prima;
  - accruals (Sloan).
- **Analisti**: revisioni delle stime EPS a 30 e 90 giorni (su contro giù), sorpresa dell'ultima trimestrale (SUE), raccomandazione media, prezzo obiettivo medio (con min e max) e numero di analisti.
- **Fiducia interna**: acquisti degli insider a mercato negli ultimi 90 giorni, con evidenza degli acquisti di gruppo (≥ 3 insider), e short interest.
- **Formule in Appendice A.** Ogni indicatore ha una scheda `armorInfo`.

**45.5 Eventi e notizie per titolo (il cuore della richiesta «leggere le notizie e interpretarle»).** Senza AI a pagamento: tre livelli, dal più affidabile al più incerto.
1. **Eventi ufficiali SEC 8-K (USA)**, dal feed «current filings» o dalle submissions per CIK. Gli **item** dicono già cosa è successo:
   - 1.01 = contratto rilevante firmato;
   - 1.03 = fallimento;
   - 2.02 = risultati trimestrali;
   - 2.05/2.06 = ristrutturazioni o svalutazioni;
   - 3.01 = avviso di delisting;
   - 4.02 = bilanci non affidabili (restatement);
   - 5.02 = uscita di dirigenti;
   - 7.01/8.01 = altri annunci; il titolo dell'allegato 99.1 è il comunicato stampa.
2. **Titoli delle notizie**: `yfinance Ticker.news`, Google News RSS (`https://news.google.com/rss/search?q="NOME"+stock&hl=en-US`), comunicati stampa. **Classificazione a regole** con il dizionario della Appendice B (EN, con l'esito tradotto in IT). Cause: risultati sotto le attese, taglio delle previsioni, approvazione FDA, rifiuto FDA (CRL), studio clinico riuscito o fallito, aumento di capitale o diluizione, contratto vinto (con estrazione dell'importo via regex: «$1.2 billion», «€300 million» → **% del fatturato annuo**), partnership, acquisizione, declassamento o promozione degli analisti, indagine o causa seria, rapporto di uno short seller, uscita del CEO, richiamo prodotto, dazi o regole, notizia di settore o macro.
   - **Ignorare lo spam degli studi legali** («investor alert», «class action reminder», Rosen, Pomerantz, Levi & Korsinsky…), che appare dopo ogni calo e non dice nulla di nuovo.
   - Il tono viene da FinBERT (esistente).
   - Solo quando le regole non trovano nulla, classificazione «zero-shot» con un modello aperto piccolo che gira su CPU in Actions (es. `MoritzLaurer/deberta-v3-base-zeroshot-v2.0`), limitata a ~200 titoli al giorno. Se il tempo non basta: «causa non identificata».
3. **Confronto con settore e mercato.** Rendimento in eccesso = titolo − β × ETF di settore nello stesso periodo. Se il settore è sceso quasi quanto il titolo, la causa è «settore/mercato», non l'azienda.

**45.6 Farmaci e biotecnologie (esempio dell'utente: un farmaco nuovo fa volare un titolo).**
- **ClinicalTrials.gov API v2** (`https://clinicaltrials.gov/api/v2/studies?query.spons=<azienda>`): studi di fase 2 e 3 con la data di completamento primario nei prossimi 6 mesi (catalizzatori in arrivo) e gli esiti appena pubblicati.
- **openFDA** (`https://api.fda.gov/drug/drugsfda.json`): approvazioni per sponsor.
- **Date PDUFA** prese dalle notizie con la regex «PDUFA … date of <data>».
- **Etichetta «rischio binario»** per le biotech con un solo prodotto e ricavi quasi nulli: l'esito di un solo studio può dimezzare o raddoppiare il prezzo, e va scritto in chiaro.

**45.7 Temi tecnologici (esempio dell'utente: una notizia sulla robotica fa salire altri titoli).** Dizionario dei temi: robotica, AI, semiconduttori, nucleare e SMR, quantum, spazio, difesa, farmaci per l'obesità (GLP-1), cybersecurity, reti elettriche e data center, editing genetico, batterie e litio. Per ognuno: parole chiave IT/EN, ETF di riferimento, elenco titoli collegati (dalle partecipazioni degli ETF tematici, file pubblici dei gestori, più le parole chiave nella descrizione dell'azienda).

**Forza del tema** =
- 50% accelerazione del volume di notizie (GDELT DOC 2.0 API gratuita, `mode=timelinevolraw`: volume delle ultime 2 settimane contro le 12 precedenti);
- 50% forza relativa dell'ETF del tema a 1 e 3 mesi contro MSCI World.

Quando un tema accelera, i titoli collegati ricevono un «vento a favore», usato in Opportunità. La pagina mostra i temi caldi della settimana con le notizie che li hanno mossi.

---

## PATCH 46 — «Saldi»

**46.1 Cosa mostra (aggiornata ogni giorno di borsa).**
- Pulsanti periodo: **1 giorno · 3 giorni · 1 settimana · 1 mese · 3 mesi · 6 mesi**.
- Per ogni periodo, i **100 titoli/ETF dell'universo filtrato che sono scesi di più**. Filtri: tipo (Azioni / ETF), area (USA, Europa, Asia, altri), dimensione (grandi > 10 mld, medie 2–10, piccole < 2), settore. Ordinamento per % di calo oppure per punteggio.
- **Riga o scheda per titolo (su telefono una scheda compatta, su desktop una tabella con la prima colonna fissa):**
  - nome, ticker, borsa;
  - **% del periodo**;
  - prezzo (valuta + euro);
  - **fatturato ultima trimestrale con freccia ▲/▼** (sullo stesso trimestre dell'anno prima);
  - **P/S, P/E, P/S previsto**;
  - debito netto/EBITDA, mesi di cassa (se in perdita);
  - F-score;
  - una **etichetta della causa** (es. «Risultati sotto le attese», «Rifiuto FDA», «Calo di settore», «Nessuna notizia»);
  - **Punteggio Salute 1–100** con colore.
- **Al tocco, scheda di dettaglio**:
  - grafico 6 mesi;
  - tutti gli indicatori della 45.4 con le schede ⓘ;
  - le 3–5 notizie che spiegano il calo, tradotte e con link;
  - **il report** (46.3).

**46.2 Punteggio Salute 1–100 (100 = azienda in ottima salute, calo con cause temporanee, storicamente buona probabilità di recupero; 1 = gravissime difficoltà).** Si basa su prove documentate:
- dopo un **calo senza notizie** o **dovuto al settore** i prezzi tendono a recuperare nel breve (inversione di breve periodo: Jegadeesh 1990, Lehmann 1990; Chan 2003: i perdenti «senza notizie» recuperano, quelli «con notizie» continuano a scendere);
- dopo **risultati sotto le attese o previsioni tagliate** il calo tende a proseguire per settimane (deriva post-annuncio, PEAD: Bernard & Thomas 1989);
- su 3–12 mesi i perdenti tendono a restare perdenti (momentum: Jegadeesh & Titman 1993), salvo aziende solide e a buon prezzo (Piotroski 2000, Asness et al. «Quality minus Junk»).

| componente | peso | contenuto |
|---|---|---|
| Solidità finanziaria | 30% | Altman Z (o Z''), copertura interessi, debito netto/EBITDA, current ratio, mesi di cassa, diluizione |
| Qualità e tendenza del business | 25% | F-score, crescita fatturato a/a e sua tendenza, margine lordo e tendenza, margine FCF, ROIC |
| Natura del calo | 20% | il rendimento in eccesso sul settore indica quanto il calo è specifico; causa (45.5): settore/mercato o nessuna notizia = positivo; aumento di capitale = leggermente negativo; risultati sotto attese e previsioni tagliate = negativo (soprattutto nei periodi brevi); rifiuto FDA o studio fallito su una biotech mono-prodotto = molto negativo |
| Valutazione dopo il calo | 15% | P/S, P/E, P/S previsto, EV/EBITDA rispetto alla mediana del settore e alla mediana a 5 anni del titolo |
| Segnali di fiducia | 10% | acquisti degli insider dopo il calo, revisioni delle stime, riduzione dello short interest |

Regole di calcolo:
- Ogni voce si trasforma in percentile all'interno dell'universo e del settore (con winsorizzazione al 2–98%). La media pesata va in percentile e poi su scala `1 + 99 × p`.
- **Tetti obbligatori (massimo 15/100)**: dubbio sulla continuità aziendale, item 1.03 (fallimento), 3.01 (delisting), 4.02 (restatement), rapporto di short seller con accuse di frode non smentite, mesi di cassa < 6 senza finanziamento annunciato.
- I pesi sono il **punto di partenza**, registrati in `PROTOCOLLO_SALDI.md` prima di qualsiasi verifica. Si cambiano solo una volta l'anno e solo se la verifica (46.4) lo giustifica.
- **Etichetta nell'app:** «Salute e probabilità di recupero stimate» — mai «rimbalzo sicuro».

**46.3 Report per titolo (italiano, generato a regole, senza AI a pagamento).** Quattro blocchi di 2–4 frasi ciascuno, costruiti da modelli di frase con i dati veri:
- **«Perché è sceso»**: causa classificata, notizie principali, confronto con il settore (es. «Il titolo ha perso il 18% in 3 giorni; il suo settore solo il 2%: il calo è legato all'azienda. Il 6/11 ha pubblicato ricavi sotto le attese (−4%) e ha abbassato le previsioni per il 2027.»).
- **«Come sta l'azienda»**: debito, cassa, margini, tendenza del fatturato, con frecce.
- **«Perché potrebbe essere acquistabile»**: solo i punti realmente favorevoli (es. «valutazione scesa a 1,8 volte il fatturato contro 3,5 della mediana del settore», «tre dirigenti hanno comprato azioni dopo il calo», «contratti già firmati pari a 2,1 anni di fatturato»).
- **«Rischi principali»**: sempre presente, mai vuoto.

Chiusura fissa: «Non è una consulenza: è una sintesi automatica di dati pubblici».

**46.4 Verifica continua (lo storico rende il punteggio credibile).** Ogni giorno salva in `data/saldi_registro.csv` data, ticker, periodo, punteggio, prezzo e le componenti. Un job ricalcola i rendimenti a 1 mese e 3 mesi (e il calo massimo). La pagina mostra la tabella **«Quanto ha funzionato il punteggio»**: rendimento medio e % di titoli in rialzo per fascia di punteggio (1–20 … 81–100), contro l'ETF di settore. Per avere subito una prima stima: **test storico** sui titoli USA con i dati SEC per data di deposito (dal 2012, prezzi yfinance), dichiarando che è ottimista perché include solo i titoli ancora quotati (survivorship bias).

---

## PATCH 47 — «Opportunità» (ogni settimana le 30 aziende più promettenti)

**47.1 Cosa mostra.**
- **Le 30 aziende** con il punteggio più alto della settimana, con filtri per area e dimensione.
- Per ognuna:
  - rendimento a 7 giorni e a 1 mese;
  - prezzo;
  - **fatturato ultima trimestrale con freccia**;
  - **P/S, P/E, P/S previsto**;
  - capitalizzazione/RPO (se c'è);
  - **Punteggio Potenziale 1–100**;
  - i **tre motivi principali** (es. «stime degli analisti alzate del 12% in 30 giorni», «contratto da 800 M$ = 40% del fatturato», «tema Robotica in forte accelerazione»);
  - i **catalizzatori in arrivo** (data trimestrale, PDUFA, fine di uno studio);
  - **la crescita stimata a 1 mese, 3 mesi, 1 anno e 2 anni** (47.3).
- Scheda di dettaglio come in Saldi, con il report a regole: «Perché è promettente» e «Cosa potrebbe andare storto».
- **Temi della settimana** in testa alla pagina (da 45.7).

**47.2 Punteggio Potenziale 1–100 (100 = caratteristiche che storicamente hanno dato i rendimenti futuri migliori; 1 = le peggiori).** Modello multi-fattore con fattori documentati in letteratura:

| fattore | peso iniziale | misura |
|---|---|---|
| Revisioni delle stime | 20% | variazione EPS e ricavi attesi a 30/90 giorni, rapporto revisioni su/giù (tra i segnali più robusti documentati) |
| Momentum | 15% | rendimento 12 mesi escluso l'ultimo mese, vicinanza al massimo a 52 settimane (George & Hwang 2004) |
| Crescita | 15% | crescita fatturato a/a, **accelerazione** (crescita di questo trimestre meno quella del precedente), «regola del 40» per il software |
| Qualità | 15% | profittabilità lorda / attivo (Novy-Marx 2013), ROIC, accruals bassi, F-score |
| Sorpresa e deriva | 10% | sorpresa dell'ultima trimestrale (SUE) e reazione del prezzo nei 3 giorni dopo |
| Contratti e visibilità | 10% | RPO o backlog in crescita, RPO/capitalizzazione, contratti 8-K item 1.01 o USAspending recenti rispetto al fatturato |
| Catalizzatori e temi | 10% | eventi positivi classificati negli ultimi 30 giorni (approvazione FDA, studio riuscito, contratto, partnership con grandi aziende, previsioni alzate) + forza del tema (45.7) |
| Valutazione ragionevole | 5% | P/S previsto rispetto alla crescita (PSG) e al settore, per evitare chi è già carissimo |

Regole di calcolo:
- Ogni fattore in percentile all'interno di regione e settore. Somma pesata, poi percentile, poi `1 + 99 × p`.
- **Filtri prima del punteggio**: capitalizzazione ≥ 300 M$ (small cap incluse, microcap no), controvalore ≥ 1 M$/giorno, almeno 3 analisti oppure dati SEC completi.
- Pesi registrati in `PROTOCOLLO_OPPORTUNITA.md`. Un test storico sui titoli USA con dati SEC per data di deposito (2012–oggi) serve **solo** a controllare che il punteggio abbia senso (decili ordinati). I pesi non si ottimizzano sui dati per non sovra-adattarli.

**47.3 Crescita stimata a 1 mese / 3 mesi / 1 anno / 2 anni (onesta).** Non è una promessa ma una **fascia** costruita così:
- **Centro**: rendimento mediano storico dei titoli nella stessa fascia di punteggio, preso dal test storico e poi sostituito dallo storico reale man mano che si accumula.
- **Ampiezza**: volatilità del titolo × √t (t in anni), con quantili 10–90 della distribuzione empirica (non normale).
- **Visualizzazione**: «mediana +8% · 8 casi su 10 tra −15% e +35%».
- Quando la parte alta della fascia supera +100% si mostra in multipli («scenario favorevole: ×2»), **sempre insieme** alla parte bassa.
- A parte, il **prezzo obiettivo medio degli analisti** a 12 mesi (min–max e numero di analisti).
- Mai «crescita certa».

**47.4 Storico delle settimane (richiesto esplicitamente).** Ogni sabato salva in `data/opportunita_registro.csv` le 30 scelte con prezzo, punteggio e fasce previste. La pagina «Storico» mostra una tabella per settimana: titolo, previsione mediana a 1 mese e 3 mesi, **risultato reale** (verde se dentro o sopra la fascia, rosso se sotto), più il riepilogo:
- rendimento medio delle 30 scelte contro MSCI World e VWCE nello stesso periodo;
- % di titoli che hanno battuto il mercato;
- % di risultati dentro la fascia 10–90 (dovrebbe stare vicino all'80%: se no, le fasce si correggono).

Lo storico va mostrato anche quando è negativo.

**47.5 Aggiornamento.** Job settimanale `opportunita.yml`, sabato mattina:
1. universo filtrato;
2. pre-selezione sui prezzi e sulle revisioni (le 600 migliori per momentum + revisioni + eventi);
3. fondamentali e notizie;
4. punteggio;
5. report;
6. registro.

Il job ha tempo massimo 120 minuti e salva i risultati parziali se qualcosa fallisce. In settimana, nel job giornaliero, si aggiornano solo prezzi e notizie delle 30 scelte.

---

## Appendice A — Formule

- **Piotroski F-score (0–9)**, 1 punto per ciascuno: ROA > 0; flusso di cassa operativo > 0; ROA in crescita; flusso operativo > utile netto; leva a lungo termine in calo; current ratio in aumento; nessuna nuova emissione di azioni; margine lordo in aumento; rotazione dell'attivo in aumento.
- **Altman Z (manifatturiere)** = 1,2·(capitale circolante/attivo) + 1,4·(utili non distribuiti/attivo) + 3,3·(EBIT/attivo) + 0,6·(capitalizzazione/passività totali) + 1,0·(ricavi/attivo). Zona critica < 1,81; sicura > 2,99.
- **Altman Z'' (non manifatturiere ed emergenti)** = 6,56·X1 + 3,26·X2 + 6,72·X3 + 1,05·(patrimonio netto contabile/passività). Critica < 1,1; sicura > 2,6.
- **Mesi di cassa** = (cassa + investimenti a breve) / (−flusso di cassa libero trimestrale) × 3, solo se il flusso è negativo.
- **Diluizione** = azioni in circolazione oggi / un anno fa − 1.
- **Accruals (Sloan)** = (utile netto − flusso di cassa operativo) / attivo medio: più basso è meglio.
- **SUE** = (EPS effettivo − EPS atteso) / deviazione standard delle sorprese degli ultimi 8 trimestri; in mancanza, sorpresa % semplice.
- **Momentum 12-1** = prezzo di 1 mese fa / prezzo di 12 mesi fa − 1.
- **Rendimento in eccesso** = r_titolo − β·r_ETF settore, con β stimato su 1 anno di dati giornalieri.
- **Pressione accumulata (Regime)** = Σ λ^k · max(0, Armor_{t−k} − 40), λ = 0,97.
- **Percentile → punteggio**: `score = round(1 + 99 × rank_pct)`.

## Appendice B — Dizionario eventi (prime parole chiave, da completare)

| evento | parole chiave (EN) | effetto in Saldi | effetto in Opportunità |
|---|---|---|---|
| Risultati sotto attese | misses, below estimates, falls short, revenue miss | negativo | — |
| Previsioni tagliate | cuts guidance, lowers outlook, withdraws guidance | molto negativo | — |
| Previsioni alzate | raises guidance, raises outlook | — | positivo |
| Approvazione FDA | FDA approves, FDA approval, granted approval | — | molto positivo |
| Rifiuto FDA | complete response letter, CRL, FDA declines | molto negativo (tetto se mono-prodotto) | — |
| Studio riuscito | met primary endpoint, positive topline, statistically significant | — | positivo |
| Studio fallito | did not meet, failed to meet, discontinued trial | molto negativo | — |
| Aumento di capitale | public offering, priced offering, at-the-market, registered direct | leggermente negativo | negativo |
| Contratto vinto | awarded, wins contract, order worth, multi-year agreement | — | positivo (pesato su % del fatturato) |
| Acquisizione (bersaglio) | to be acquired, agrees to be bought, buyout | escludere dalla lista | escludere |
| Indagine seria | SEC investigation, DOJ, subpoena, accounting irregularities | tetto 15 se non smentita | escludere |
| Short seller | short report, Hindenburg, Muddy Waters, short seller | negativo, valutare la smentita | — |
| Spam legale (da ignorare) | investor alert, class action reminder, shareholder rights law firm, Rosen, Pomerantz, Levi & Korsinsky, Bragar | ignorare | ignorare |
| Delisting / fallimento | Chapter 11, bankruptcy, delisting notice, minimum bid price | tetto 5–15 | escludere |

## Appendice C — Ordine e dipendenze

40 (grafico) → 41 (Oggi, Semafori, schede) → 42 (Notizie) → 43 (Regime) → 44 (Mercati) → 45 (Motore titoli) → 46 (Saldi) → 47 (Opportunità).

- 44 usa il filtro liquidità di 45: nel frattempo, per la categoria Titoli, usa solo i titoli dei principali indici (S&P 500, STOXX 600, Nikkei 225); l'universo completo arriva con 45.
- 46 e 47 richiedono 45.
- Tempi stimati di GitHub Actions: Mercati ~10 min/giorno, Saldi ~30–45 min/giorno, Opportunità ~60–120 min/settimana. Restano gratuiti se il repository è pubblico; se è privato, controlla i minuti mensili e dillo all'utente.
