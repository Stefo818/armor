# PROTOCOLLO — Elementi spia suggeriti da due testi esterni (23 novembre 2026)

Scritto e pubblicato PRIMA di calcolare qualsiasi risultato. Dopo la pubblicazione non si cambiano soglie, definizioni né regole.

## Perché
L'utente ha portato due testi generati da un assistente (elenco di «elementi spia» di un crollo, e un «triangolo» di tre segnali che indicherebbe un crollo immediato).
Domanda: quali di questi elementi, nei dati, hanno davvero anticipato i crolli di natura finanziaria, e vale la pena aggiungerli all'Indice crollo o ad Armor?
I testi sono affermazioni, non prove: le trattiamo come ipotesi da verificare. Perimetro invariato: **solo crisi finanziarie** (stesse finestre di esclusione di PROTOCOLLO_GARA_INDICI.md: dazi, guerre, pandemia, più 2026-02-25).

## Cosa si può e cosa non si può provare
Già misurato da Armor, non si ripete come novità: valutazioni (CAPE, Buffett), richieste di sussidio, livello del credito, VIX e sua curva, rotazione fra settori, grandi fondi.
Non provabile con i dati gratuiti che abbiamo: vendite dei dirigenti (insider), riacquisti di azioni proprie, quotazioni in Borsa speculative (IPO), la «narrativa questa volta è diverso», indice PMI ufficiale (ISM), ampiezza vera del mercato (percentuale di titoli sopra la media a 200 giorni: i dati iniziano ad agosto 2025, troppo pochi). Per l'ampiezza si usano due sostituti con storia lunga, dichiarati qui sotto.

## Candidati (21). Ogni serie è orientata in modo che «più alto = più rischio»
Ritardi di pubblicazione applicati (giorni di calendario) per non guardare nel futuro: mensili 35-50 giorni, settimanali 5, giornalieri 0.
- C01 curva 10 anni meno 2 anni, invertita: −t10y2y
- C02 curva 10 anni meno 3 mesi, invertita: −t10y3m
- C03 «disinversione» 2a-10a: variazione a 63 sedute di t10y2y se la curva è stata invertita (<0) in almeno una seduta delle 252 precedenti, altrimenti 0 (risale dopo un'inversione)
- C04 come C03 con t10y3m
- C05 ciclo di rialzi: variazione a 252 sedute del tasso della banca centrale americana (fedfunds)
- C06 regola di Sahm (sahm), ritardo 35
- C07 indagine manifatturiera: −philly (ritardo 20)
- C08 ordini di beni durevoli: −variazione annua di neworder (ritardo 35)
- C09 permessi di costruzione: −permit_yoy (ritardo 45)
- C10 impulso del credito: variazione a 10 sedute dello spread baa10y
- C11 livello dello spread baa10y (riferimento)
- C12 ampiezza dei settori: numero dei 9 fondi settoriali (sec_xlb…sec_xlu) sotto la loro media a 200 giorni, **solo** se l'S&P 500 è entro il 5% dal suo massimo a 252 sedute, altrimenti 0 (divergenza: indice in alto, struttura che cede)
- C13 ampiezza dei settori semplice: stesso numero senza condizione
- C14 ampiezza per pesi uguali: −(rendimento a 63 sedute del rapporto rsp/spy)
- C15 debito per comprare azioni (margin_yoy), ritardo 50
- C16 debito a margine contro prezzi: margin_yoy meno rendimento a 252 sedute dell'S&P 500 (punti percentuali), ritardo 50
- C17 SKEW (costo delle protezioni contro il crollo): skew
- C18 oro: rendimento a 63 sedute di gold
- C19 dollaro: rendimento a 21 sedute di dxy
- C20 yen forte: −variazione a 21 sedute del cambio dollaro/yen (JPY=X da Yahoo; se non scaricabile con storia giornaliera dal 1996 il candidato è escluso e lo si dichiara)
- C21 euforia dei consumatori: umcsent, ritardo 40

Ogni candidato diventa un punteggio con la **percentuale espansa** (rango storico dal primo dato fino a oggi, minimo 252 osservazioni, senza guardare il futuro).

## Bersagli e periodi (identici alla gara degli indici)
Una settimana: calo ≥3% dal prezzo di oggi entro 5 sedute; un mese: ≥5% entro 21; tre mesi: ≥8% entro 63. Minimo futuro misurato dal prezzo di oggi.
Scelta: dall'inizio dei dati di ciascun candidato al 2014; verifica: 2015-2026. Giorni fuori dal perimetro finanziario esclusi come nella gara.

## Prove
**P1 — da solo.** AUC (probabilità che un giorno pre-crollo abbia punteggio più alto di uno normale) nella scelta e nella verifica, per ogni candidato e ogni orizzonte, con intervallo al 90% per blocchi d'anno.
Soglia del caso: migliore su 21×3=63 prove quando i bersagli sono mescolati a blocchi d'anno (120 mescolamenti, 95° percentile). Promosso da solo se: AUC verifica ≥ 0,60, estremo basso dell'intervallo > 0,50 e AUC verifica > soglia del caso.
**P2 — valore aggiunto.** Base: Indice crollo (livello giornaliero). Misto = 0,8 × rango(base) + 0,2 × rango(candidato), pesi fissi, nessuna taratura. Si confrontano base e misto sugli stessi giorni.
Adottabile se, sia nella scelta sia nella verifica, il misto migliora l'AUC di almeno +0,010 in almeno 2 orizzonti su 3 e nessuno peggiora di più di 0,010.
**P3 — il «triangolo» dei testi.** Tre condizioni: A = impulso del credito (C10) sopra l'80° percentile; B = «disinversione» attiva (C03 > 0 e sopra il suo 80° percentile); C = ampiezza che cede (C12 ≥ 3 settori sotto la media) **e** debito a margine alto (C15 sopra l'80° percentile). Si contano: giorni con A, B, C tutte accese; giorni con almeno 2 su 3; episodi indipendenti (separati da almeno 60 sedute); quota di questi giorni seguita da un calo ≥8% entro 63 sedute contro la base; quante delle crisi finanziarie dal 1990 (elenco di classifica_40anni.py) avevano il triangolo acceso nei 63 giorni prima del calo del 10%. Con pochi episodi il risultato è un ordine di grandezza, non una probabilità.

## Etichette e onestà
Esiti ammessi: «Coerente con i casi osservati» oppure «Non coerente». Mai «provato». Si dichiarano sempre: numero di episodi, candidati esclusi per dati insufficienti, e che una prova passata sui soli dati storici non garantisce il futuro.
Se un candidato supera P1 o P2 si integra nell'app solo dopo un secondo protocollo di adozione. Questa pagina non cambia l'app.
