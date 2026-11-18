# Protocollo «Crisi lente 2: due chiavi» (scritto il 18 novembre 2026, PRIMA di calcolare qualunque risultato)

## Richiesta
Mercato moderno (dal 1990). Una scheda che anticipi i ribassi lenti usando **due chiavi**: (1) il credito facile e abbondante seguito da una brusca salita dei tassi, (2) la stretta del credito, la mancanza di liquidità; incrociando inflazione, tassi, mutui e altro.

## Ammissione di partenza
Dal 1990 gli episodi di ribasso lento sono pochissimi (2000-02, 2007-09, 2022), e la prima prova li aveva già in parte visti. Le due chiavi sono state pensate guardando quelle crisi (**pregiudizio a posteriori dichiarato**). Per questo il punteggio non ha alcun parametro stimato sui dati (solo percentili e minimo/massimo), e l'esito massimo ammesso è «coerente con i casi osservati», **mai «provato»**. Il vero giudice sarà il registro in avanti.

## Bersaglio (S&P 500, chiusure giornaliere)
A fine di ogni mese t, **ribasso lento (RL)** = calo massimo ≥ 15% entro 504 sedute (2 anni) **e** il prezzo di t non viene più raggiunto per almeno 378 sedute (18 mesi). Casi attesi: 2000-02, 2007-09, 2022; i cali recuperati in meno di 18 mesi (1990, 1998, 2011, 2015, 2018, 2020) non contano.
**Solo mesi «non ancora in crisi»:** si valutano solo le date in cui l'S&P 500 è entro il 5% dal suo massimo di 252 sedute. Così il punteggio deve anticipare l'inizio e non descrivere una crisi già in corso. Ultima data valutabile: novembre 2024.

## Punteggio (nessun parametro stimato)
Ogni variabile → **percentile** del suo valore rispetto alla storia dal gennaio 1990 fino a quel mese (solo passato, minimo 60 mesi), con il verso sotto (inv = basso vuol dire più rischio, si usa 1 − percentile). Ritardi di pubblicazione in mesi.
- **Credito facile (Boom)**, media di: crescita dei prestiti alle imprese a 6 mesi (alto, 1); crescita del debito privato in 5 anni (alto, 5); extra-rendimento BAA-AAA (inv, 1); stretta bancaria alle grandi imprese (inv, 2); debito per comprare titoli, variazione annua (alto, 2); crescita annua di M2 (alto, 2).
- **Scossa dei tassi (Shock)**, media di: variazione a 12 mesi del tasso a 3 mesi (alto, 1); del rendimento a 10 anni (alto, 0); del tasso dei mutui a 30 anni (alto, 0); tasso reale della banca centrale (alto, 1); inflazione annua (alto, 1); curva 10 anni meno 3 mesi (inv, 1).
- **Chiave 1** = minimo tra Boom e Shock (servono entrambi: credito abbondante **e** tassi che salgono).
- **Chiave 2 (Stretta)** = media di: stretta bancaria alle grandi imprese (alto, 2), alle piccole (alto, 2), sulle carte (alto, 2); extra-rendimento BAA-AAA (alto, 1); condizioni del credito NFCI (alto, 0); carte non pagate (alto, 5); mutui non pagati (alto, 5); crescita dei prestiti alle imprese (inv, 1).
Ogni media richiede almeno metà delle variabili disponibili.
- **Allarme «attenzione»** = massimo tra Chiave 1 e Chiave 2 ≥ 0,80. **Attenzione moderata** = ≥ 0,65.
Contesto, non nel punteggio: percentile delle valutazioni (CAPE), che dice quanto sarebbe lungo il recupero.

## Prove
1. **Episodi**: gruppi di mesi RL (nella serie dei mesi «non ancora in crisi») separati da più di 12 mesi. Per ciascuno: allarme acceso almeno un mese nei 24 mesi prima del primo mese RL? Quale chiave? Con quanti mesi di anticipo?
2. **Falsi allarmi**: quota di mesi con allarme tra i mesi non RL (stesso insieme); e quota del tempo totale in allarme.
3. **AUC** del punteggio (max delle due chiavi) per RL, con intervallo a blocchi di 24 mesi; confronto con: Chiave 1 sola, Chiave 2 sola, Boom da solo, Shock da solo, CAPE da solo, tendenza (prezzo sotto la media a 10 mesi), e punteggio «Terreno lento» della prima prova.
4. **Sosia**: 200 punteggi con la stessa struttura (stesse formule di percentili, minimo, massimo) ma serie di rumore. L'AUC vero deve superare il 95° percentile.

## Etichetta (fissata ora; nessun numero cambia dopo)
- **Coerente con i casi osservati** se: allarme acceso prima di tutti gli episodi nei 24 mesi precedenti; falsi allarmi ≤ 25%; AUC ≥ 0,70; AUC sopra il 95° dei sosia.
- **Non coerente** altrimenti.
In entrambi i casi la scheda nell'app dice che non è provata e riporta il numero dei casi. Con «non coerente» la scheda resta solo informativa.

## Limiti
Tre episodi in trent'anni: nessuna statistica regge. Dati «come oggi». Il 2022 è un caso di tassi e inflazione: se la chiave 1 non lo vede, l'idea del credito facile + tassi in salita non è sostenuta.

---
# Emendamento 1 (18 novembre 2026, stesso giorno, scritto dopo aver visto che la definizione del bersaglio era degenerata e PRIMA di leggere AUC e allarme su un bersaglio valido)

**Cosa è successo.** Alla prima esecuzione il bersaglio RL, come scritto sopra («il prezzo di t non viene più raggiunto per 378 sedute»), dava 1 solo mese positivo su 231: per qualunque mese prima del massimo il prezzo viene ritoccato salendo, quindi la condizione non era mai vera. Non misurava «l'inizio di un ribasso lento», che era l'intenzione. Il risultato di quell'esecuzione (AUC non calcolabili, 1 caso) non dice nulla sull'ipotesi.
**Definizione corretta (stessa intenzione, soglie invariate: 15% e 18 mesi).**
- Si individuano gli **episodi di ribasso lento** nelle chiusure dell'S&P 500: dal massimo (peak) fino al ritorno a quel massimo (recupero), con calo massimo ≥ 15% e durata dal massimo al recupero ≥ 378 sedute (18 mesi). Un episodio non ancora recuperato conta se dura già da ≥ 378 sedute.
- **RL(t) = 1** per i fine-mese da 504 sedute prima del massimo fino alla prima seduta in cui il calo dal massimo raggiunge −10%. Vale ancora la restrizione «solo mesi entro il 5% dal massimo di 252 sedute».
- Il resto del protocollo (punteggio, allarme, prove, etichetta) non cambia.
**Limite dichiarato:** la nuova definizione è stata scritta conoscendo i tre episodi; è guidata dall'intenzione, non da un esito del punteggio.
