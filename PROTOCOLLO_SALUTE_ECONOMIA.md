# Protocollo: «Salute dell'economia» calibrata sulle recessioni (con PIL di USA ed Europa)

Scritto il **25/11/2026 (sera)**, prima di calcolare un solo risultato. Nessuna regola si cambia dopo aver visto i numeri.

## Richiesta dell'utente
L'indice «Salute dell'economia» (oggi 88, media con peso uguale di lavoro e produzione, costi e tassi, famiglie e mutui, in percentili) sembra troppo alto. Si vuole: (1) aggiungere il PIL di USA ed Europa; (2) **fissare a 100 le forti recessioni del passato** e regolare i pesi di conseguenza, per avere un valore attendibile sulla condizione reale dell'economia di oggi; (3) provare tutte le alternative possibili e scegliere la migliore.

## Misure (tutte «alto = peggio», valori grezzi, non percentili; ritardi reali di pubblicazione)
- **Lavoro e produzione (L1-L7):** sussidi di disoccupazione (media 4 settimane sul minimo a 52, ritardo 5 gg), posti di lavoro (var. 3 mesi, invertita, 37 gg), produzione industriale (3 mesi, invertita, 45 gg), indice di Chicago (invertito, 45 gg), permessi di costruzione (6 mesi, invertiti, 45 gg), indicatore di Sahm (40 gg), fiducia dei consumatori (6 mesi, invertita, 20 gg).
- **PIL (G1-G2), nuovo:** PIL reale USA (GDPC1) e PIL reale area euro (CLVMNACSCAB1GQEA19), variazione su 12 mesi, invertita; ritardo 120 giorni dalla data d'inizio del trimestre (prima stima), senza modellare le revisioni. Disoccupazione e produzione dell'area euro: serie ferme al 2023, escluse.
- **Costi e tassi (K1-K5):** inflazione (12 mesi), sua accelerazione (6 mesi), petrolio WTI (12 mesi), rialzo del tasso Fed (12 mesi), rialzo dei tassi a 2 anni (12 mesi).
- **Famiglie e mutui (M1-M7):** tasso del mutuo (variazione 12 mesi e livello), mutui non pagati, carte non pagate, stretta delle banche sul credito alle famiglie, credito al consumo (crescita invertita), quota del reddito per i debiti.
I valori mancanti (serie non ancora esistente) valgono 0 dopo la standardizzazione (neutro). Standardizzazione (media e scarto) calcolata solo sul periodo di addestramento.

## Bersaglio T (fissato ora): «gravità dell'economia», 0-100
Recessioni dell'NBER, mesi di fine mese, da gennaio 1990 a oggi. **Forti** (T = 100): dic 2007-giu 2009 e feb-apr 2020. **Lievi** (T = 60): lug 1990-mar 1991 e mar-nov 2001. Dopo la fine di ogni recessione T scende in linea retta fino a 0 in 12 mesi dal valore della recessione (si sta ancora male). Fuori da questi periodi T = 0.

## Modello: punteggio lineare calibrato
Indice = taglio a 0-100 di (a + somma pesata dei valori standardizzati), con a e i pesi stimati su T nel periodo di addestramento (minimi quadrati; pesi ≥ 0). Così il livello 100 corrisponde alla gravità media delle forti recessioni e il resto dei pesi è guidato dai dati.

## Alternative (N = 24; più 2 riferimenti, non valgono per il «migliore»)
Pesi uguali con una sola pendenza stimata: E1 = L · E2 = L+G · E3 = L+G+M · E4 = L+G+K · E5 = tutte le 21 misure · E6 = G da solo · E7 = media di 4 pilastri (L,G,K,M) · E8 = media di 2 pilastri (L,G).
Pesi stimati: W1 = minimi quadrati non negativi (NNLS) su tutte le 21 misure · W2 = NNLS su L+G · W3 = NNLS su L+G+M · W4 = ridge (lambda 10, pesi negativi portati a 0) su tutte · W5 = ridge su L+G · W6 = NNLS sui 4 pilastri (medie) · W7 = NNLS su 3 pilastri L,G,M · W8 = NNLS su L+G+K.
Altre: X1 = regressione logistica (C=0,1) sulla recessione NBER, tutte le misure, probabilità poi calibrata linearmente su T · X2 = logistica su L+G · X3 = prima componente principale di tutte · X4 = componente principale di L+G · X5 = massimo dei 4 pilastri · X6 = massimo di L,G · X7 = mediana delle 21 misure · X8 = media delle 5 misure più alte fra L+G (a ogni mese).
Riferimenti: R0 = indice di oggi (percentile della media di 3 pilastri, non ricalibrato) · R1 = solo pilastro economia del Super Armor in percentile.

## Convalida: «lascia fuori una recessione»
Quattro blocchi nel tempo, ognuno contiene una recessione (1990-91, 2001, 2007-09, 2020) e i mesi più vicini ad essa (confini a metà strada fra due recessioni). Per ogni blocco si addestra sugli altri tre e si calcola l'indice nel blocco (fuori campione); i quattro pezzi si uniscono. Misure sul campione unito: **RMSE fra indice e T** (primaria), AUC sulla recessione NBER in corso, indice medio nei mesi di recessione forte, quota dei mesi di vera espansione (T=0, oltre 12 mesi dopo la fine) con indice ≥ 60 (falsi allarmi).

## Regole di giudizio
Si adotta l'alternativa con RMSE fuori campione più basso fra le 24, purché: (a) RMSE inferiore di almeno il 10% a quello di R0; (b) soglia «migliore fra N»: 100 spostamenti circolari di T (≥ 24 mesi), per ciascuno si rifanno tutte le 24 alternative fuori campione e si prende il RMSE minimo; il RMSE reale deve stare sotto il 5° percentile di questi minimi; (c) quota di falsi allarmi ≤ 10%. Se (a) o (b) falliscono si tiene la formula attuale ma ricalibrata (E5) e si dichiara. Se due alternative differiscono meno di 3% di RMSE, vince la più semplice (meno misure).
Dopo la scelta: pesi finali stimati su tutto il campione 1990-2026, valore di oggi e contributo di ogni pilastro, serie giornaliera dal 1990 nell'app, pesi dichiarati.

## Limiti dichiarati
Solo quattro recessioni (due forti, due lievi), una sola crisi europea in comune; PIL con ritardo lungo e senza revisioni; T è una definizione nostra, non un dato osservato; serie europee mancanti (disoccupazione, produzione). La calibrazione a 100 sulle due forti recessioni è per costruzione: un'economia in crisi diversa (per esempio da inflazione) potrebbe dare valori più bassi.
