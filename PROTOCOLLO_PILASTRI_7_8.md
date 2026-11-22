# Protocollo — Pilastro «fondi a breve contro fondi a lungo» e indice Buffett
Scritto e pubblicato **prima** di qualunque calcolo. 22 novembre 2026.

## 0. Da dove nasce, e cosa c'è già
Richiesta dell'utente: l'Indice Armor non pesa il movimento dei grandi fondi, in particolare la differenza
fra chi opera a breve termine e chi investe a lungo; e propone l'indice Buffett (valore della Borsa diviso
il prodotto interno lordo) come ulteriore pilastro.

Verifica dello stato attuale, fatta prima di scrivere: il pilastro 4 di Titan **contiene già** i grandi
fondi, ma `titan_job.py` gli passa **una sola** serie, `cot_am_net`, cioè i **gestori di patrimoni**, che
sono gli investitori a lungo termine. I **fondi con leva** (`cot_lev_net`), che sono quelli a breve
termine, e gli **intermediari** (`cot_dealer_net`) non entrano da nessuna parte. L'osservazione
dell'utente individua quindi un buco reale.

## 1. Le tre candidate, costruzione fissata ora
Tutte in percentile su storia crescente, con ritardo di pubblicazione: dati dei fondi 4 giorni (escono il
venerdì sui dati del martedì), indice Buffett 90 giorni (i conti finanziari escono circa dieci settimane
dopo il trimestre).
- **C1 fondi a breve in uscita.** Posizione netta dei fondi con leva, invertita: più scappano, più alto.
- **C2 divergenza fra breve e lungo.** Posizione netta dei gestori a lungo meno quella dei fondi con leva,
  entrambe standardizzate sul solo passato. Alta quando i fondi a breve scappano mentre i lunghi restano:
  è l'ipotesi dell'utente nella sua forma precisa.
- **C3 indice Buffett.** Valore di Borsa delle società americane diviso il prodotto interno lordo, in
  percentile su storia crescente.

## 2. Dove si provano
- **Prova A, regola già esistente del progetto** (`test_new_indicators`): ogni candidata si aggiunge alla
  famiglia più vicina dell'Indice Armor e si confronta l'area sotto la curva con e senza, sui tre eventi
  dal 2013. Si adotta solo se migliora di almeno 0,01 in almeno 2 eventi su 3 e nessuno peggiora di più di
  0,01. Famiglie: C1 e C2 in «Sentimento e ampiezza», C3 in «Valutazioni».
- **Prova B, la zona che interessa all'utente**: giorni entro il 5% dal massimo, bersaglio «il calo arriva
  al 10% entro 60 sedute», sole crisi finanziarie. Riferimento: l'Indice crollo attuale, 21,5%.

## 3. Regole di accettazione, fissate ora
- **P1** la candidata entra nell'Indice Armor se e solo se supera la Prova A con la sua regola già scritta.
- **P2** la candidata viene segnalata come utile nella zona vicino ai massimi se, nella Prova B, la
  precisione del suo quinto più alto supera la frequenza di base di almeno 8 punti.
- **P3** per diventare un **pilastro a sé** di Titan servirebbe rifare la taratura dei sei pilastri
  esistenti: non si fa in questa prova. Le candidate che passano P1 entrano come indicatori dentro una
  famiglia, non come pilastro nuovo. Questo rispetta l'avvertimento dell'audit esterno: non toccare i pesi
  di Titan v47 inseguendo un singolo episodio.
Esito possibile: «Adottata» (P1 superata) oppure «Non adottata», con i numeri in chiaro.

## 4. Limiti dichiarati prima
I dati dei fondi partono dal 20 luglio 2010: 16 anni, con sole 4 crisi finanziarie dentro (2015, 2018,
2022, 2026). Su quattro episodi nessun risultato può essere definitivo. L'indice Buffett ha storia lunga
(dal 1945) ma esce una volta al trimestre con dieci settimane di ritardo: per un segnale di crollo a
poche settimane è quasi fermo, e questo va detto qualunque sia il risultato.
