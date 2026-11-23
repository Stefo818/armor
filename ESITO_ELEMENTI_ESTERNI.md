# ESITO — Elementi spia suggeriti da due testi esterni (23 novembre 2026)

Segue PROTOCOLLO_ELEMENTI_ESTERNI.md (pubblicato prima dei calcoli, commit 0d79381). Script: scratch/elementi_esterni.py, numeri completi in scratch/elementi_esterni.json.
Perimetro: sole crisi finanziarie. Scelta fino al 2014, verifica dal 2015.

## 1. Cosa Armor già misura
Valutazioni (CAPE, Buffett), richieste di sussidio, livello del credito, VIX e sua curva, rotazione fra settori, grandi fondi: già dentro gli indici. Non si ripetono come novità.

## 2. Cosa non si può provare con dati gratuiti
Vendite dei dirigenti, riacquisti di azioni proprie, quotazioni speculative, «questa volta è diverso», indice PMI ufficiale, ampiezza vera del mercato (dati solo da agosto 2025). Per l'ampiezza: due sostituti (settori sotto la media a 200 giorni; titoli a pesi uguali contro pesi di mercato).

## 3. Prova da solo (P1) e valore aggiunto (P2)
21 candidati x 3 orizzonti = 63 prove. Soglia del caso (migliore su 63 con bersagli mescolati, 95° percentile): **0,7771**.
- **Nessun candidato promosso (P1). Nessuno adottabile (P2).** Etichetta: «Non coerente con i casi osservati» per tutti.
- Molti segnali classici sembrano forti nel passato lontano e si capovolgono dopo il 2015 (AUC scelta → verifica): livello dello spread del credito a tre mesi 0,774 → 0,328; regola di Sahm 0,709 → 0,434; indagine manifatturiera 0,675 → 0,459; ordini di beni durevoli 0,667 → 0,294; permessi di costruzione 0,633 → 0,467. Sono i segnali dell'economia reale e del credito: le crisi dopo il 2015 sono nate più da valutazioni, tassi e liquidità che da recessione e credito.
- Curva dei rendimenti invertita (10a-2a): nella scelta nessun segnale (0,49-0,50), nella verifica 0,63-0,69 con intervalli larghi: instabile. Con 3 mesi (10a-3m) nessun segnale in entrambi i periodi. La «disinversione» (risalita dopo l'inversione) non dà segnale (0,50-0,53 nella scelta; 0,55-0,61 nella verifica; con 3 mesi addirittura 0,39-0,56).
- Il più coerente in entrambi i periodi: **ampiezza dei settori semplice** (quanti dei 9 settori sono sotto la media a 200 giorni): scelta 0,73/0,69/0,72, verifica 0,66/0,65/0,62 (settimana/mese/tre mesi). Ma sotto la soglia del caso, con intervalli che scendono sotto 0,50 a un mese e a tre mesi, e il valore aggiunto sull'Indice crollo è nullo o piccolo (da -0,008 a +0,017): non adottabile.
- Contrari: SKEW (0,33-0,49 in verifica), oro (0,42-0,43), euforia dei consumatori (0,32-0,34), debito a margine (0,42-0,55), yen forte e dollaro (≈0,50): nessun segnale, in alcuni casi segnale rovesciato.

## 4. Il «triangolo» dei testi (P3)
Impulso del credito (A) + disinversione della curva (B) + ampiezza che cede con debito a margine alto (C).
- **Tutte e tre insieme: 0 giorni in 36 anni.** Con le definizioni fissate non si è mai verificato: come regola per riconoscere un crollo imminente, non ha mai potuto scattare.
- Singole: A 1.263 giorni, 43 episodi, calo dell'8% entro tre mesi nel 28% dei casi (base 16,8%); B 1.435 giorni, 13 episodi, 31%; C 45 giorni, 3 episodi, 87% (campione troppo piccolo).
- **Almeno due su tre:** 336 giorni, 17 episodi indipendenti, calo dell'8% entro tre mesi nel **38%** dei casi contro 16,8%. Ma diviso per periodo: scelta (fino al 2014) 267 giorni, 8 episodi, 42,7% contro 17,8%; **verifica (dal 2015) 69 giorni, 9 episodi, 20,3% contro 13,9%**. Il vantaggio quasi sparisce nel periodo recente.
- Richiamo su 14 crisi finanziarie valutabili (63 sedute prima del calo del 10%; i picchi precedenti al 1990 non sono valutabili): triangolo 0/14, almeno due 6/14, solo A 11/14, solo B 6/14, solo C 1/14.
- Oggi: A, B e C spenti. Prima del picco del 6 ottobre (calo attuale) erano accesi A e C.

Correzione di implementazione dichiarata: nella prima esecuzione il calcolo del richiamo associava a episodi minori (-8,5% del 2024) un calo successivo non collegato; è stato corretto limitando la ricerca a 150 sedute dal picco e togliendo i picchi precedenti al 1990. Le regole del protocollo non sono cambiate.

## 5. Verifica dei fatti nei testi
Il secondo testo racconta il crollo di novembre 2026 come «settimana peggiore, causata dalle indagini della SEC su Nvidia». Una ricerca sulle cronache conferma il contesto (azioni dell'intelligenza artificiale in affanno, Nvidia al centro, dimissioni di Huang, timori sui tassi) ma non conferma l'indagine della SEC; l'IPO da 7 miliardi citata non è verificata. Il testo ha un valore narrativo, non documentale.

## 6. Conclusione
Nessun elemento dei due testi migliora in modo dimostrabile la previsione. Gli indici non cambiano. Resta come osservazione da seguire nel tempo, non come regola: «almeno due su tre» fra impulso del credito, disinversione e ampiezza+debito.
Limiti: 14 crisi finanziarie, pochi episodi indipendenti nella verifica, un solo mercato, segnali esaminati uno per uno e in un solo modo di costruirli.
