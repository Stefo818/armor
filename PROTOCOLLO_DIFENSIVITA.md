# Protocollo: «Difensività dei grandi fondi» (scritto il 24/11/2026 ore 15:25, prima di calcolare qualunque risultato)

## Domanda (utente)
Se i grandi fondi accumulano liquidità o passano a obbligazioni/oro, si aspettano un calo? Un indice che misura questo comportamento difensivo prevede i crolli, o dice altro?
Ipotesi concorrenti scritte ora: **H1 (anticipo)** = più difensivi → più calo dopo. **H2 (seguono)** = i fondi diventano difensivi *dopo* il calo, e la loro difensività alta segnala che il peggio è passato (rimbalzo). Entrambe si testano.

## Dati (già nel repository) e ritardi di pubblicazione
Fondi monetari USA (`mmf_assets`, settimanale dal 1980, ritardo 2 giorni; l'ultimo dato nel repository è del 05/10/2026: si usa quel che c'è, dichiarato); oro (`gold`, dal 2000) e S&P 500 (`sp500`) per la forza relativa; TLT (`tlt`, dal 2002) per le obbligazioni lunghe; posizione netta dei fondi a leva e dei gestori patrimoniali sui futures S&P 500 (`cot_lev_net`, `cot_am_net`, dal 2010, ritardo 4 giorni); quota di protezioni dichiarata nei 13F dei grandi fondi (`grandi_fondi.json`, `f13_protezione`, trimestrale dal 2013, ritardo 46 giorni).

## Costruzione (percentili solo del passato, espandenti; più alto = più difensivo)
- D1 liquidità: variazione a 52 settimane dei fondi monetari meno la variazione a 52 settimane dell'S&P 500 (liquidità che cresce più del mercato), percentile. D1b: variazione a 13 settimane, percentile.
- D2 oro contro azioni: log(oro/S&P 500) variazione a 63 sedute, percentile.
- D3 obbligazioni contro azioni: log(TLT/S&P 500) variazione a 63 sedute, percentile.
- D4 fondi a leva: 1 − percentile della posizione netta; D5 gestori patrimoniali: 1 − percentile della posizione netta.
- D6 protezioni 13F: percentile (dal 2013).
Indici: **DIF-L (lungo)** = media di D1, D1b, D2 disponibili (dal 1981); **DIF-C (completo)** = media di tutti i disponibili (almeno 4, dal 2013), poi di nuovo percentile. Minimo 104 settimane (2 anni) di storia per i percentili.

## Test (tutti sull'S&P 500, esclusi gli shock esterni e il 1973 come in PROTOCOLLO_TERRITORI.md)
**T1 Anticipo.** Stati: difensivo alto (DIF-L ≥ 0,80) e difensivo basso (≤ 0,20). Bersagli B1 −8% entro 63 sedute, B2 −12% entro 63 sedute. DR con intervallo al 90% per anno, blocchi 1981-2014 (scelta) e 2015-2026 (verifica); soglia del «migliore fra N» (N = 2 stati × 2 bersagli × 2 indici = 8) con 500 spostamenti circolari. **Dimostrato** (H1) solo se IC90 > 0 in entrambi i blocchi su entrambi i bersagli, DR di verifica sopra la soglia, ≥ 6 episodi indipendenti; altrimenti indizio (DR > 0 in entrambi i blocchi) o non supportato. Se DR è significativamente negativo in entrambi i blocchi: la difensività è un segnale contrario (H2 compatibile).
**T2 Rimbalzo (H2).** Giorni con l'S&P 500 ≥ 10% sotto il massimo a 252 sedute (almeno 126 giorni, ≥ 4 episodi): rendimento a 63 sedute per terzili della difensività (alta vs bassa), differenza mediana con intervallo al 90% a blocchi per anno. «Utile» solo se la differenza è positiva con IC90 > 0 sia prima sia dal 2015.
**T3 Strato di conferma.** Giorni con Bolla o Credito (Sick Index, ≥ 70) accesi: P(B1) con difensività bassa contro alta (DR), stesso intervallo e stessi blocchi. «Utile» solo se DR ha lo stesso segno in entrambi i blocchi e IC90 > 0 sul periodo intero.
**Solo descrittivo:** DIF-C dal 2013 (periodo troppo corto per una prova).

## Cosa entra nell'app, deciso ora
Qualunque esito: l'indice viene registrato ogni giorno (`data/difensivita_registro.csv`) con peso zero. Mostrato nel Quadro solo se T1 o T2 o T3 è «dimostrato/utile» (riga sotto il Sick Index: «Grandi fondi: difensivi / non difensivi», con la lettura ammessa dai test: anticipo, rimbalzo o conferma). Se nessuno lo è: solo registro e nota nell'esito.

## Limiti dichiarati
Gli investitori istituzionali privati non pubblicano la liquidità in modo diretto: i fondi monetari includono anche aziende e famiglie; il COT riguarda un solo mercato; il 13F è trimestrale e in ritardo. I dati dei fondi monetari nel repository finiscono il 05/10/2026.
