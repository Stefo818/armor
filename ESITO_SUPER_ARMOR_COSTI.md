# Esito: inflazione, petrolio, tassi, mutui e debiti delle famiglie nel Super Armor (25 novembre 2026)

Segue PROTOCOLLO_SUPER_ARMOR_COSTI.md (con addendum delle 18:15), scritto prima dei calcoli. Script: scratch/super_armor_costi.py, numeri in scratch/super_armor_costi_esito.json. Campione comune da agosto 2006 (petrolio), scelta 2006-2014, verifica 2015-2026; 14 varianti nuove.

## Risposta
**Nessuna variante entra nel punteggio: la formula del Super Armor resta «il più alto fra finanza ed economia».** Le nuove misure vengono mostrate come pilastri **senza peso** («Costi e tassi», «Famiglie e mutui») e alimentano le indicazioni flash.

## Numeri (correlazione con l'economia a 6 mesi; V0 = formula attuale: scelta +0,68, verifica +0,45)
- Inflazione, petrolio, rialzo dei tassi (V1-V8): **tutte peggiorano** in entrambi i blocchi (Δ verifica da −0,12 a −0,63; V1 «terzo pilastro costi»: −0,46).
- Famiglie e mutui (W1-W6): W1, W2, W4, W5 ≈ invariate; **W3 (tassi dei mutui e accesso) +0,07 e W6 (media dei tre pilastri) +0,09 in verifica con limite inferiore > 0**, ma W3 in scelta è 0,00 (regola a) e W6 non supera la soglia del migliore-fra-14 (0,56, regola c): **non adottate**. W6 resta come candidata in prova in avanti (valore giornaliero nel registro).
- Misure da sole (Spearman con l'economia a 6 mesi; alto = peggio, atteso +): **banche che stringono il credito alle famiglie +0,51** (la migliore), carte di credito non pagate +0,39, quota del reddito per i debiti +0,46 (ma −0,26 in 2006-2014), livello del tasso del mutuo +0,25, inflazione +0,20. **Segno opposto al previsto:** rialzo dei tassi (−0,07/−0,23), variazione del petrolio (−0,24), accelerazione dell'inflazione (−0,12), variazione del tasso del mutuo (−0,07): salgono nelle espansioni e scendono nelle recessioni, quindi nel campione non anticipano il peggioramento. Mutui non pagati ≈ 0.
- Un'unica recessione (2008) in scelta e una (2020, shock esterno) in verifica: prove deboli; 2022 (inflazione e tassi) non è stata una recessione.

## Oggi (percentili storici, 0-100, alto = peggio)
Costi e tassi 69: inflazione 77, accelerazione 57, petrolio 77, rialzo tassi 52, rialzo tassi a 2 anni 82. Famiglie e mutui 45: rialzo del tasso del mutuo 89, tasso del mutuo 60, mutui non pagati 20, carte non pagate 31, stretta delle banche 47, debito sul reddito 22 (credito al consumo si aggiunge appena l'accumulo scarica TOTALSL).

## Dati
Aggiunti all'accumulo giornaliero (FRED): TOTALSL, REVOLSL, MDSP, CDSP, DRTSPM, HHMSDODNS, HCCSDODNS, SLOAS, CPIAUCSL, CUSR0000SEHA, CUSR0000SETB01, GASREGCOVW, DRTSCILM. Già presenti: MORTGAGE30US, MORTGAGE15US, DRSFRMACBS, DRCCLACBS, DRTSCLCC, TDSP, HDTGPDUSQ163N, DCOILWTICO, DCOILBRENTEU, CPILFESL, PCEPI.

## Salute dell'economia (indice nuovo, richiesta dell'utente delle 18:19)
Indice staccato dall'Indice Armor e dal Super Armor: **da 1 (economia in ottima salute) a 100 (economia allo sfascio)**, descrive l'economia di oggi (il Super Armor guarda ai prossimi mesi). È la media con **peso uguale** di tre pilastri: lavoro e produzione (le 7 misure dell'economia del Super Armor), costi e tassi (inflazione, accelerazione, petrolio, rialzo dei tassi, rialzo a 2 anni) e famiglie e mutui (7 misure), portata a posizione storica 1-100. Costruzione chiesta dall'utente («anche se non passa»): non è una scelta della prova.
Misura descrittiva (non una selezione): quanto bene il valore separa i giorni di recessione già in corso (NBER, 1990-2026, 753 giorni): lavoro e produzione da soli AUC 0,98 · con le famiglie 0,98 · con costi e tassi 0,78 · **tutti e tre 0,87**. Costi e tassi abbassano la capacità di riconoscere le recessioni (salgono anche nelle espansioni). Oggi: 88 (lavoro e produzione 54, costi e tassi 69, famiglie e mutui 45); con il solo pilastro lavoro e produzione il percentile è 65. Nella zona 80-100 l'economia era in recessione nel 32% dei giorni (media di sempre 8%).
La descrizione dell'indice nell'app lo dichiara.
