# Protocollo — Indice crollo

Scritto, salvato e pubblicato il 22 novembre 2026 **prima** di calcolare qualunque risultato di prestazione.
Dopo la pubblicazione non si cambia nessuna soglia, nessun bersaglio, nessuna regola di accettazione.
Richiesta dell'utente: un numero da 1 a 100 in cima alla scheda Oggi che dica quanto è vicino un crollo.

## 0. Cosa si sa già, dichiarato prima di partire
Queste cose sono state misurate **prima** di scrivere il protocollo e sono proprietà del mercato o
dell'archivio, non risultati del modello. Sono dichiarate qui perché hanno guidato il disegno.

Frequenze di base sull'S&P 500, dal 1990 (9.290 sedute):
- almeno −4% nel minimo delle 5 sedute successive: 5,7% dei giorni (530 casi)
- almeno −5% nel minimo delle 10 sedute successive: 8,0% dei giorni (742 casi)
- almeno −8% nel minimo delle 21 sedute successive: 7,1% dei giorni (664 casi)

Quanto indietro vanno le serie dell'archivio Armor:
- dal 1990 o prima: paura (VIX), inclinazione delle opzioni, costo delle protezioni, differenziale
  obbligazioni societarie meno Stato, tassi a 2 e 10 anni, dollaro, prezzo e volatilità dell'S&P 500.
- dal 2000 al 2007: curva della paura (VIX a 3 e 6 mesi), paura della paura, volatilità dei titoli di
  Stato, forza relativa di semiconduttori, piccole società, banche, ciclici, trasporti, rame contro oro,
  obbligazioni ad alto rendimento, Indice Armor.
- **meno di due anni, quindi non verificabili**: ampiezza del mercato a 50 e 200 giorni, nuovi massimi
  meno nuovi minimi, differenziali di credito ad alto rendimento e investment grade, indice di paura e
  avidità, concentrazione dei primi titoli. Queste possono entrare nella scheda come contesto ma **non**
  possono essere validate e quindi **non** determinano l'etichetta.

## 1. Bersagli
Calcolati sull'S&P 500 perché è il motore del VWCE e ha la storia più lunga.
- **Primario (Y10):** il minimo delle 10 sedute successive è almeno il 5% sotto la chiusura di oggi.
  Corrisponde a «un paio di settimane» nella richiesta dell'utente.
- **Secondario (Y5):** il minimo delle 5 sedute successive è almeno il 4% sotto la chiusura di oggi.
  Corrisponde a «pochi giorni».
Periodo: dal 2 gennaio 1990 al 20 novembre 2026.

## 2. Ritardi di pubblicazione, obbligatori
Nessuna variabile può usare un dato che non era pubblico quella mattina.
- Serie di prezzo e di borsa (indici, volatilità, rapporti fra titoli): chiusura dello stesso giorno.
- Serie giornaliere della Federal Reserve (tassi, differenziali, dollaro): ritardo di 1 seduta.
- Serie settimanali (condizioni finanziarie): ritardo di 7 giorni di calendario.
- Serie mensili o trimestrali: ritardo di 30 giorni di calendario.
Controllo obbligatorio: ricalcolando la serie dopo aver tagliato gli ultimi 30 giorni di dati, il valore
dell'indice in una data precedente non deve cambiare di più di 0,5 punti.

## 3. Famiglie di segnali
Una sola variabile rappresentativa per famiglia, scelta con la regola fissata qui: quella con la storia
più lunga; a pari storia, quella con meno valori mancanti.
1. **Livello della paura**: paura a 1 mese, in percentile su storia crescente.
2. **Salto della paura**: variazione della paura su 5 e 10 sedute.
3. **Curva della paura**: paura a 1 mese divisa per quella a 3 mesi (sopra 1 = allarme).
4. **Costo delle protezioni**: inclinazione delle opzioni e indice delle protezioni.
5. **Credito**: differenziale obbligazioni societarie meno titoli di Stato, livello e variazione a 20 sedute.
6. **Tassi**: variazione del tasso a 10 anni su 5 e 20 sedute, inclinazione 10 anni meno 2 anni.
7. **Tendenza**: distanza del prezzo dalla media a 50 e a 200 giorni, e da quanto la media a 200 è rotta.
8. **Perdita in corso**: distanza dal massimo degli ultimi 12 mesi.
9. **Volatilità realizzata**: deviazione dei rendimenti a 20 sedute e sola parte negativa.
10. **Rotazione difensiva**: forza relativa di semiconduttori, piccole società, banche, rame contro oro.
11. **Volatilità dei titoli di Stato**.
12. **Indice Armor** esistente, come dodicesima famiglia e anche come riferimento da battere.
Trasformazione fissata: ogni variabile diventa un percentile su storia crescente, con almeno 500
osservazioni precedenti, senza mai guardare il futuro.

## 4. Modelli da provare
Si provano tutti e cinque, nessuno viene scartato prima del confronto.
- **M1** composito: media semplice dei percentili delle 12 famiglie.
- **M2** composito pesato a mano con pesi fissati ora: paura e curva della paura 0,30; credito 0,15;
  tendenza e perdita in corso 0,25; rotazione difensiva 0,15; tassi 0,15 (normalizzati a 1).
- **M3** regressione logistica su finestra crescente, rifatta ogni 21 sedute.
- **M4** alberi potenziati (gradient boosting, profondità massima 3, 200 alberi, learning rate 0,05) su
  finestra crescente, rifatti ogni 63 sedute.
- **M5** regola a due chiavi: allarme se almeno due famiglie fra paura, curva della paura, credito e
  tendenza sono oltre il loro 85° percentile.
- **Riferimento**: Indice Armor esistente.

## 5. Scelta del modello e periodo di verifica, separati
- Il modello vincente si sceglie **solo** sui dati dal 1990 al 2014, con il criterio fissato qui: area
  sotto la curva (AUC) più alta sul bersaglio primario; a pari merito, frequenza più alta nella fascia viola.
- La prestazione riportata nell'esito è quella sul periodo **dal 2015 al 2026**, mai usato per scegliere.
- In entrambi i periodi il calcolo è a finestra crescente: ogni giorno usa solo il passato.

## 6. Mappatura sulle fasce di colore richieste dall'utente
Il punteggio del modello diventa un percentile su storia crescente, poi un numero da 1 a 100 con questa
scala fissata ora (lineare dentro ogni tratto):
| percentile del punteggio | indice | colore richiesto | quota attesa dei giorni |
|---|---|---|---|
| sotto 0,55 | 1–35 | verde | 55% |
| 0,55–0,65 | 36–40 | grigio | 10% |
| 0,65–0,85 | 41–60 | giallo | 20% |
| 0,85–0,96 | 61–80 | rosso | 11% |
| sopra 0,96 | 81–100 | viola | 4% |
La fascia viola deve restare rara, circa dieci giorni l'anno: è questo che la rende un'informazione.

## 7. Regole di accettazione, fissate ora
Sul periodo dal 2015 al 2026 e sul bersaglio primario:
- **R1** AUC almeno 0,65 e limite inferiore dell'intervallo al 90% sopra 0,55.
  Intervallo con bootstrap a blocchi di 21 sedute, 1.000 ripetizioni.
- **R2** nella fascia viola la frequenza del bersaglio è almeno 2,5 volte quella di base.
- **R3** test placebo: 200 spostamenti circolari del bersaglio; il 95° percentile delle AUC finte deve
  stare sotto l'AUC vera.
- **R4** batte l'Indice Armor di almeno 0,02 di AUC, oppure lo pareggia con frequenza più alta nella
  fascia viola.
Tutte e quattro soddisfatte: etichetta **«Coerente con i casi osservati»**, l'indice va in cima a Oggi.
Anche una sola non soddisfatta: etichetta **«Non coerente»**, l'indice si mostra comunque ma dichiarato
come contesto, e nel testo si dice che non ha superato la prova.
Non si userà mai la parola «provato».

## 8. Come si scrivono le parole nelle fasce, regola di onestà
Il testo di ogni fascia riporta la **frequenza misurata** in quella fascia, non un giudizio.
Le parole «molto probabile» si possono usare **soltanto** se la frequenza misurata in quella fascia supera
il 50%. Sotto il 50% il testo dirà «è successo N volte su 100». Questa regola vale anche se la frequenza
misurata è molto più alta di quella di base: tre volte il rischio normale resta una minoranza di casi.
Si dichiara sempre, nella scheda, che l'indice non prevede i crolli improvvisi e che la maggior parte dei
giorni in fascia viola non è seguita da un crollo.

## 9. Controlli aggiuntivi obbligatori nell'esito
- Frequenza misurata e numero di casi per ogni fascia, con intervallo al 90%.
- Quanti episodi di calo di almeno il 10% dal 1990 sono stati preceduti da almeno un giorno giallo o
  peggio nei 10 giorni precedenti, e quanti no.
- Quanti giorni gialli o peggio **non** sono stati seguiti da nulla (falsi allarmi), in numero e in quota.
- Replay esplicito di due date vicine e opposte: 5 novembre 2026 (allarme senza crollo) e
  18 novembre 2026 (vigilia del crollo). Se l'indice non sa distinguerle, va detto.
- Stabilità: AUC sulle due metà del periodo di verifica e solo dal 2020.

## 10. Limiti da dichiarare comunque
Gli episodi veri di crollo sono pochi: dal 1990 si contano poche decine di episodi indipendenti, quindi
ogni numero ha un margine ampio. I dati gratuiti arrivano con ritardo. Le serie di ampiezza del mercato
hanno meno di due anni e non entrano nella validazione. Un indice tarato sul passato può mancare un
crollo di tipo nuovo.
