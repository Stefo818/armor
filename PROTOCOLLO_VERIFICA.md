# PROTOCOLLO DI VERIFICA ARMOR — versione 1, datato 8 novembre 2026

Scritto **prima** di verificare qualsiasi variante del nuovo motore di percorsi (PIANO_ARMOR3 Fase 2). Dopo questa data le regole non si cambiano:
se servono regole diverse si scrive un protocollo nuovo (versione 2) con la data, e quello vecchio resta come prova. L'impronta (SHA-256) di questo file
viene scritta in `data/protocollo_log.csv` (e nel diario v3) il giorno del rilascio: se il file cambia, l'impronta non torna e l'app lo segnala.

## 1. Ruoli
- **Riferimento ufficiale**: il numero principale mostrato dall'app. Oggi A1 (regressione logistica sui prezzi dell'S&P 500) a tutti gli orizzonti.
- **Sfidante**: mostrato accanto, etichettato «sperimentale». **Ombra**: calcolato e registrato, non mostrato come previsione.
- Il riferimento cambia solo per la regola di adozione storica (§4), orizzonte per orizzonte, e può tornare ad A1 per la regola di ritorno (§5).

## 2. Dati e metodo (uguali per tutti i modelli)
- Previsioni walk-forward: una data ogni 5 sedute, dal 1994 a oggi, solo con dati noti a ogni data; parametri rifatti ogni anno, con distanza di 5 sedute
  (A1: ogni 63 sedute, con gli esiti già maturati). Date comuni a tutti i modelli confrontati.
- Esito: calo massimo rispetto al prezzo di oggi nelle h sedute successive, almeno pari alla soglia (non è il «massimo drawdown»: quello è un altro obiettivo).
  Orizzonti: 7, 21, 63, 126 sedute (le «10 giorni, 1 mese, 3 mesi, 6 mesi» dell'app). Soglia principale: quella di `config.PRIMARY` (5%, 10%, 10%, 10%).
  Le altre soglie dello stesso orizzonte si riportano a titolo informativo e non entrano nella regola.
- «Normale» = frequenza degli esiti già maturati alla data (purge: date ≤ t − h).
- Metriche (`verifica.py`): Brier, BSS rispetto al normale, log loss, AUC, curva di affidabilità a 10 classi, errore di calibrazione medio, pendenza di calibrazione.
- Sovrapposizione delle finestre: **bootstrap stazionario** (2.000 repliche, blocco medio = ⌈h / 5⌉ osservazioni, seme fisso), **sottocampioni non sovrapposti**
  (date con almeno h sedute di distanza, per tutti gli sfasamenti possibili; si riportano media e dispersione), **numero di episodi** (eventi separati da meno di h sedute = un episodio).
- Confronti: differenza di Brier rispetto ad A1 sulle stesse date, test di Diebold-Mariano con errori HAC (ritardo ⌈h / 5⌉ − 1), correzione di Holm sulle varianti dello stesso orizzonte.
- Prove multiple: PBO con il metodo CSCV (16 blocchi di tempo) sulla matrice «varianti × blocchi» del Brier.
- Distribuzioni: copertura della fascia 10-90 (e 5-95) del rendimento finale, CRPS dai quantili. Volatilità: QLIKE.
- Ogni prova va in `data/ricerca/registro_prove.csv`, anche quelle fallite.

## 3. Varianti pre-registrate (Fase 2)
Il confronto riguarda solo queste. Non se ne aggiungono dopo aver visto i risultati.
- Varianza iniziale: **V0** (FHS attuale), **V1** (FHS+VIX: peso 0,5, premio 0,8), **V2** (struttura a termine del VIX con varianza forward e rapporto realizzata/implicita stimato in walk-forward).
- Controllo delle code: **T0** (nessuno), **T1** (tetto alla varianza al 99,5° percentile), **T2** (ancoraggio di lungo periodo dal giorno 63), **T3** (blocchi storici riscalati per la volatilità).
- 12 varianti (V0-V2 × T0-T3). Riferimento del confronto: A1. Holm su 12 confronti per orizzonte.
- Se un dato necessario non esiste (ad esempio VIX a 3 mesi o a 6 mesi nel periodo), la variante V2 si calcola solo dove i dati esistono e lo si scrive; la regola di adozione richiede le stesse date di A1.

## 4. Regola di adozione storica (per migliorare subito senza aspettare anni)
A ogni orizzonte (7, 21, 63, 126 sedute) una variante diventa riferimento ufficiale al posto di A1 **solo se valgono tutte** queste condizioni sulla verifica walk-forward 1994-oggi:
1. differenza di Brier rispetto ad A1 con intervallo bootstrap al 90% tutto a favore della variante (estremo superiore < 0) **sul campione intero**; sui **sottocampioni non sovrapposti**
   la media delle differenze è < 0 e la mediana degli estremi superiori degli intervalli (uno per sfasamento) è < 0; il p di Diebold-Mariano corretto con Holm è < 0,10;
2. BSS positivo sia nel 1994-2012 sia nel 2013-oggi;
3. pendenza di calibrazione tra 0,8 e 1,2;
4. copertura della fascia 10-90 tra il 77% e l'83%;
5. PBO sotto 0,5 tra le 12 varianti.

Una condizione che non si può valutare conta come non superata. Se più varianti passano si sceglie: (a) CRPS più basso a quell'orizzonte; (b) a parità entro 1%, errore di calibrazione medio più basso;
(c) a parità, la più semplice (ordine V0 < V1 < V2, poi T0 < T1 < T2 < T3). Se nessuna passa, A1 resta e il motore resta sperimentale.
In app una variante adottata è etichettata «adottato sulla verifica storica, in conferma dal vivo».

Limiti dichiarati: il 2019-2026 è già stato visto in ricerche precedenti, quindi non è un campione pulito; per questo le 12 varianti nascono da difetti misurati e da motivazioni teoriche, non da una ricerca di parametri,
e la conferma finale spetta al diario dal vivo.

## 5. Conferma dal vivo e regola di ritorno
- Ogni variante adottata è registrata nel diario v3 insieme ad A1 (stessi giorni).
- Revisione descrittiva: **10 maggio 2027** (solo numeri, nessuna decisione). Non si guardano i risultati per decidere fuori dalle date del protocollo.
- Prima data di decisione: **8 novembre 2028**, poi ogni 6 mesi. Finestre indipendenti minime: 1 mese ≥ 24; 3 mesi ≥ 8; 6 mesi ≥ 4. Sotto queste soglie si scrive «prova insufficiente» e non si decide.
- Se a una data di decisione, con finestre sufficienti, la differenza di Brier della variante rispetto ad A1 nel diario dal vivo ha estremo inferiore dell'intervallo bootstrap al 90% > 0 (cioè la variante è peggiore oltre l'incertezza), il riferimento torna ad A1 a quell'orizzonte.
- Dichiarazione onesta: a 3-12 mesi la prova dal vivo richiede anni; nel frattempo vale la verifica storica, con un controllo dal vivo «non peggiore».

## 6. Cosa non si fa
Non si usano medie tra modelli, non si cambiano soglie dopo aver visto i risultati, non si promette che il modello diventerà «più preciso»: la direzione del mercato resta imprevedibile.
