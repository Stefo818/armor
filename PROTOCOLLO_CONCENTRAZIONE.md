# Protocollo «Concentrazione del mercato» (bozza del 24/11/2026, da approvare prima di guardare qualsiasi risultato)

## Ipotesi dell'utente
Quando il mercato è troppo sbilanciato su un settore (tecnologia) o su poche aziende (le 10 maggiori) **e** lo sbilanciamento accelera, il mercato si indebolisce e tende a calare. Vale per gli ultimi ~36 anni (dal 1990).

## Cosa si può misurare (dati gratuiti disponibili, storia verificata il 24/11/2026)
Non esistono gratis i pesi storici delle singole aziende o dei settori. Si usano **proxy di prezzo** (rapporti fra indici), tutti con storia lunga:
| Misura | Proxy | Inizio |
|---|---|---|
| Peso della tecnologia (Nasdaq vs resto) | ^NDX / ^GSPC | 1985 |
| Idem, solo tecnologia S&P | XLK / SPY | 1999 |
| Concentrazione sulle grandi (le 100 maggiori vs le 500) | ^OEX / ^GSPC | 1982 |
| Peso delle grandissime (cap-weighted vs pesi uguali) | SPY / RSP; ^GSPC / ^SPXEW | 2003; 2006 |
| Grandi vs medie aziende | ^GSPC / ^MID, ^OEX / ^MID | 1981 |
| Concentrazione dei volumi nei 10 titoli più scambiati | d_quota_volume_top10 (nostro, da 503 titoli) | 2015 |
Il numero esatto «peso % delle 10 maggiori» oggi si può solo stimare: non è dimostrabile all'indietro.

## Indici costruiti
1. **Livello**: posizione percentile (solo passato, finestra espansa) del logaritmo di ogni rapporto; media dei rapporti disponibili in ciascun anno (la lista cambia con la storia disponibile, ma ogni rapporto resta nel suo percentile).
2. **Accelerazione**: variazione a 63 giorni del logaritmo del rapporto e **variazione della variazione** (63 giorni contro i 63 precedenti), entrambe in percentile storico.
3. **Stato combinato**: «sbilanciato e accelera» = livello ≥ 80° percentile **e** accelerazione ≥ 80° percentile; «sbilanciato ma fermo»; «riequilibrio» = livello alto e accelerazione negativa.

## Bersagli (financial-only, stesse finestre ESTERNI delle altre ricerche)
a) calo massimo dell'S&P 500 nei 21 e nei 63 giorni successivi ≥ 5% / ≥ 8% / ≥ 10%; b) rendimento a 63 giorni; c) Nasdaq 100 vs S&P 500 a 63 giorni (rotazione).

## Regole
- Scelta e soglie sul periodo ≤ 2014, verifica su ≥ 2015 (e verifica «a ritroso» su 1985-1999 come prova di stabilità, non per scegliere).
- Soglia del migliore tra N: rimescolamento degli anni (blocchi annuali), 1000 volte, si dichiara N = (numero di rapporti × 3 finestre × 3 bersagli).
- Intervallo di confidenza al 90% con ricampionamento per anno.
- «Dimostrato» solo se il segnale supera la soglia nel campione di scelta **e** nella verifica, nella stessa direzione.
- Si misura anche il valore aggiunto: il segnale aggiunge qualcosa all'Indice crollo e al Terreno fragile? (confronto con e senza, nei giorni in cui l'Indice crollo è basso).
- Episodi indipendenti previsti: pochi (1998-2000, 2007?, 2018, 2021-22, 2024-26). Si dichiarano e si mostrano uno per uno. Sotto i 6 episodi indipendenti l'esito non può essere «dimostrato».
- Esito scritto in ESITO_CONCENTRAZIONE.md anche se negativo. Nell'app solo se «dimostrato»; altrimenti solo scheda informativa con la scritta «non dimostrato».
- Avvertenza dell'ipotesi contraria da verificare: nel 2023-25 la concentrazione è salita molto per anni con il mercato in crescita (segnale alto senza crollo). Un rialzo prolungato con concentrazione alta è un risultato possibile e va riportato.
