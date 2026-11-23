# Esito: anticipo dell'Indice crollo (23 novembre 2026)

Protocollo: PROTOCOLLO_ANTICIPO.md (commit ec8ee90, scritto prima dei calcoli). Script: scratch/anticipo.py. Dati: scratch/anticipo.json.

## Diagnosi: l'utente ha ragione
- L'Indice crollo è soprattutto reattivo: le famiglie «reattive» (paura, prezzo sotto le medie, distanza dal massimo, ballo dei prezzi) pesano il 71% del punteggio.
- Correlazione di Spearman: con i 5 giorni PRECEDENTI −0,29, con il calo massimo dei 5 giorni SUCCESSIVI −0,14. Segue il prezzo più di quanto lo preceda.
- Il giorno prima del primo −3% in 5 sedute, da vicino ai massimi, nelle 14 crisi finanziarie dal 1994 l'indice era sotto 41 in 11 casi (valori 3, 15, 17, 25, 26, 31, 33, 34, 36, 36, 40). Alto solo in 1997-10, 2000, 2024 (53–75).
- La «predisposizione» P (media di valutazioni, debito a margine, credito, protezioni, tassi, rotazione, titoli di Stato, condizioni finanziarie, liquidità) il giorno prima era 55–82 in tutti i 14 casi.

## Prova (bersaglio «crollo a freddo»)
Episodi indipendenti: B5 20 in scelta, 9 in verifica; B10 14 e 6 (pochi in verifica).
AUC scelta/verifica su B5: BASE 0,658/0,742 · R 0,702/0,748 · P 0,711/0,606 · M5 0,659/0,706 · E3 0,664/0,747 · B1 0,698/0,703 · B2 0,702/0,690.
Su B10: BASE 0,711/0,706 · P 0,704/0,520 · B1 0,722/0,622 · B2 0,741/0,596.
Regola di adozione (+0,03 su B5 e B10 in entrambi i periodi, senza peggiorare i controlli): **nessun candidato la passa**. Etichetta: «Non coerente».
Tenere alto l'indice con il massimo degli ultimi 5 giorni (M5) o con la media esponenziale non migliora l'anticipo. La predisposizione P da sola funziona in scelta (0,71) ma non in verifica (0,61 e 0,52): alta quasi sempre, quindi poco selettiva.

## Cosa cambia nell'app
- L'Indice crollo NON cambia: nessuna variante dimostra di avvisare prima.
- Aggiunta una riga separata «Terreno fragile» (la predisposizione P, oggi 66 su 100, media), con i tre fattori più alti (oggi: Borsa grande rispetto all'economia 100, mercato caro rispetto agli utili 96, costo delle assicurazioni sul ribasso 93). Dice la fragilità di fondo, non il giorno.
- Registro giornaliero data/predisposizione_registro.csv per la prova in avanti.

## Limiti
- I crolli «a freddo» (2018-01, 2007-07, 2020-09) arrivano da mercati calmi: con questi dati il giorno prima non c'è nulla che li distingua da migliaia di giorni calmi.
- Pochi episodi in verifica (9 e 6): niente è «provato».
- Nessun dato di intraday o di posizionamento giornaliero (opzioni a breve, flussi) per la storia: sono i candidati per una prossima ricerca in avanti.

## Emendamento 1: l'ipotesi «troppo peso alla paura» (script scratch/anticipo2.py, dati scratch/anticipo2.json)
Peso attuale della paura (f1 + f3) nel punteggio: 39%.
AUC su «crollo a freddo» (B5 scelta/verifica; B10 scelta/verifica):
BASE 0,658/0,742; 0,711/0,706 · NP senza paura 0,530/0,578; 0,576/0,589 · RP solo prezzo 0,640/0,536; 0,678/0,597 · NP2 senza paura e prezzo 0,541/0,503; 0,490/0,561 · P 0,711/0,606; 0,704/0,520 · C1 0,666/0,613; 0,674/0,545 · C2 0,634/0,565; 0,599/0,541.
Bersaglio «paura in arrivo» (VIX sotto 22 che sale di almeno 35% in 5 sedute), AUC scelta/verifica: BASE 0,364/0,471; NP 0,382/0,420; P 0,473/0,458; tutti sotto 0,5.
Adottabili: nessuno. Etichetta: «Non coerente».
Lettura: togliere la paura peggiora l'indice (da 0,74 a 0,58 in verifica): la paura è la parte che funziona, anche se arriva insieme al calo. Nessun candidato anticipa l'aumento della paura da una situazione calma (AUC sotto 0,5: quando l'indice è alto il VIX è già alto o sta scendendo). Con questi dati il salto improvviso dalla calma non è anticipabile; resta valida la sola predisposizione di fondo («Terreno fragile»), che dice quanto il mercato è delicato e non il giorno.
