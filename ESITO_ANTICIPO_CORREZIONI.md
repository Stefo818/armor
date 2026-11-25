# Esito: cosa precede una correzione endogena (5% - oltre 20%) — 25/11/2026

Protocollo: PROTOCOLLO_ANTICIPO_CORREZIONI.md (commit c20a14f + aggiunta «solo endogene» 953e7ca, prima dei calcoli). Script: scratch/anticipo_correzioni.py; dati: scratch/anticipo_correzioni_esito.json.
96 correzioni di almeno 5% dal 1990; escluse le esterne e miste: **81 endogene** (49 moderate 5-10%, 24 forti 10-20%, 8 gravi oltre 20%). Selezione 46 (picchi fino al 2007), verifica 35 (dal 2008). 120 ipotesi.

## Risultato
- Soglia contro il caso (95° percentile del massimo fra 120 ipotesi su date spostate): AUC 0,712 (mediana 0,652). **Nessuna ipotesi la supera: nessuna passa le regole.** La migliore in selezione: 0,65.
- Ipotesi dell'utente (mercato fermo vicino ai massimi, rotture fallite, stallo a 40 giorni, ombre superiori): AUC 0,47-0,55, cioè **nessun segnale**. Volume nei rialzi che cala 0,43; massimi decrescenti 0,41 (il contrario: non c'è prima, compare dopo il picco).
- Unico gruppo coerente in entrambe le metà: **il mercato è «tirato» dopo una salita rapida** (rendimento a 3-20 sedute alto, distanza dalle medie a 20 e 50 giorni alta, chiusura vicino al massimo a 20 giorni). AUC 0,61-0,66 in selezione e 0,61-0,68 in verifica; limite basso al 90% in verifica 0,55-0,62; 2-3 sedute prima fino a 0,71-0,75. Costante nelle fasce (moderate 0,64, forti 0,66-0,68, gravi 0,57-0,61). Tipicamente acceso in 37-67 correzioni su 81, 12-17 sedute prima.
- Solo per le gravi: volatilità a 20 giorni alta (0,88 sulle 8 gravi, ma 0,45 sulle moderate).
- Subito dopo il picco (E, 1-5 sedute): AUC 0,63 per rendimento a 20 sedute e per vicino al massimo a 60 giorni; il resto è debole.

## Indici dell'app prima delle correzioni endogene (AUC per fascia: moderate / forti / gravi)
- Crollo 0,41 / 0,51 / 0,72 · Armor 0,39 / 0,65 / 0,77 · Minimi 0,35 / 0,43 / 0,71 · Super Armor 0,44 / 0,64 / 0,87 · Stato 0,45 / 0,57 / 0,44.
- Le correzioni moderate partono da mercati calmi (indici sotto la media prima: Crollo 22 a 2 sedute dal picco contro 34 di base). Le gravi sono viste bene soprattutto dal Super Armor (valore ~88 a 2 sedute dal picco).

## Limiti
Correzioni a catena non indipendenti; il picco è definito col senno di poi; AUC 0,65 è un segnale debole che non passa la soglia del caso; la fase «tirato» suona anche in molti rialzi normali. Test in avanti consigliato.
