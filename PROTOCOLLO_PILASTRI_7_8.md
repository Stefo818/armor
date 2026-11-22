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

---
# Emendamento 1 (22 novembre 2026) — la prova va fatta solo sulle crisi finanziarie
Scritto **prima** di rifare i calcoli.

## A. L'errore di perimetro, dichiarato
La Prova A usa `test_new_indicators`, la regola già scritta nel progetto. Quella regola valuta i tre
eventi su **tutti** i giorni dal 2013, quindi dentro ci sono la pandemia del 2020 e le due ondate di dazi
del 2018 e del 2025. L'utente ha chiesto fin dall'inizio che il modello sia giudicato **solo** sulle crisi
di natura finanziaria: mercato troppo caro, tassi in salita, credito e liquidità che si stringono. La
Prova A come è scritta non rispetta quel perimetro, e una candidata che aiuta solo sulle crisi finanziarie
può essere bocciata da episodi che non dovrebbero contare.

## B. Prova A-bis, identica tranne il perimetro
Stessa regola di accettazione, stessi tre eventi, stesso periodo dal 2013, ma **escludendo** le finestre
di shock esterno già fissate nell'emendamento 1 di `PROTOCOLLO_INDICE_CROLLO.md` (pandemia, guerre,
attentati, dazi) e le due crisi miste. Si adotta se migliora di almeno 0,01 in almeno 2 eventi su 3 e
nessuno peggiora di più di 0,01.
Si riportano **entrambe** le prove, con e senza shock esterni: se dicono cose diverse, è un'informazione,
non un motivo per scegliere quella che conviene.

## C. Taratura della scala dell'Indice Armor, fissata ora
L'Indice Armor non supera mai 56,4 (99° percentile): le fasce sopra 60 e sopra 80 sono irraggiungibili.
Si applica una **trasformazione monotona**, che non cambia l'ordine dei giorni e quindi non cambia
nessuna AUC, nessuna prova e nessun risultato già pubblicato: cambia solo dove cadono i confini.
Regola fissata ora: i percentili dell'Indice Armor, calcolati **solo sulle crisi finanziarie** dal 1990,
vengono portati sui confini del Super Armor, che i dati già confermano (sopra 60 il calo al 10% è arrivato
nel 90,4% dei casi, sopra 80 nel 100%). I tre confini della nuova scala sono quindi il 59,6°, il 93,8° e
il 99,2° percentile dell'Indice Armor, che diventano 40, 60 e 80.
Dopo la trasformazione si **ri-misurano** le frequenze per fascia: se non corrispondono alle etichette
«difficoltà», «pericolo», «rischio crollo imminente», si cambiano le etichette, non i dati.
