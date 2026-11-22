# Protocollo — Gara fra gli indici e scheda dei quattro migliori

Scritto e pubblicato **prima** di qualunque calcolo. 22 novembre 2026.
Richiesta dell'utente: capire quale fra Indice Armor, Super Armor e Indice crollo prevede meglio i cali a
una settimana, un mese e tre mesi, misurando anche la **tensione**, cioè da quanto tempo un indice sta in
alto; e mettere in cima a Oggi una scheda compatta con i quattro valori migliori.

## 0. Il rischio principale, dichiarato prima
Tre indici per nove modi di misurarli per tre orizzonti fa **81 prove**. Scegliendo le quattro migliori su
ottantuno si trova sempre qualcosa di buono, anche se i dati fossero rumore puro. Per questo:
- la scelta si fa **solo** sui dati fino al 2014 e il risultato si riporta sul 2015-2026;
- si calcola anche la **distribuzione della migliore su 81 sotto rumore** (bersagli mescolati a blocchi),
  così si vede quanto vale «la migliore» per puro caso;
- un candidato entra nella scheda solo se batte quella soglia.

## 1. I tre indici
`armor_tarato` (Indice Armor sulla scala tarata), `super_armor_index`, `indice_crollo`. Tutti dal 1990,
tutti calcolati col solo passato.

## 2. I nove modi di misurarli, fissati ora
Per ciascun indice:
- **livello** di oggi;
- **media** delle ultime 5, 21, 63 e 126 sedute (la «tensione media» chiesta dall'utente);
- **persistenza**: quante delle ultime 5, 21, 63 e 126 sedute sono state sopra 60.

## 3. I bersagli, misurati dal prezzo di oggi
Non dal massimo a 12 mesi: quella misura gonfiava i risultati nelle fasce alte (vedi parte 7 di
`ESITO_PILASTRI_7_8.md`). Si usa il minimo futuro, così un calo poi recuperato conta comunque.
- **una settimana**: il minimo delle 5 sedute successive sta almeno il 3% sotto oggi;
- **un mese**: il minimo delle 21 sedute successive sta almeno il 5% sotto oggi;
- **tre mesi**: il minimo delle 63 sedute successive sta almeno l'8% sotto oggi.

## 4. Perimetro
Solo crisi di natura finanziaria: si escludono le finestre di shock esterno e le due crisi miste
elencate in `PROTOCOLLO_INDICE_CROLLO.md` (emendamento 1) più la guerra con l'Iran del 2026.

## 5. Scelta e verifica, separate
- Scelta: 1990-2014. Criterio: area sotto la curva più alta sul bersaglio di quell'orizzonte.
- Verifica: 2015-2026, mai usato per scegliere. È il numero che si pubblica.
- Intervalli al 90% con ricampionamento ad anni interi.

## 6. Regole di accettazione per entrare nella scheda
- **G1** area sotto la curva nella verifica almeno **0,60**, con limite inferiore dell'intervallo al 90%
  sopra **0,50**.
- **G2** deve battere il **95° percentile della migliore su 81 sotto rumore**: altrimenti non si distingue
  da ciò che il caso produce quando si sceglie il meglio di ottantuno.
- **G3** la precisione del quinto più alto deve essere almeno il doppio della frequenza di base.
Si mostrano in scheda **al massimo quattro** valori, uno per orizzonte più il migliore in assoluto; se per
un orizzonte nessun candidato supera G1-G3, per quell'orizzonte la scheda dice che **non c'è un segnale
affidabile**, e non si ripiega sul meno peggio.

## 7. Cosa risponde alla domanda «sopra 60 per una settimana, un mese, tre mesi»
Si pubblica comunque, per tutti e tre gli indici e per tutte e quattro le finestre, la tabella
«quante sedute sopra 60 nelle ultime N» contro la frequenza del calo, con il numero di giorni e di
episodi indipendenti. Anche dove non supera le regole: è una domanda esplicita dell'utente e merita la
sua risposta misurata.

## 8. Limiti dichiarati prima
Gli episodi finanziari indipendenti restano circa venti dal 1990: ottantuno prove su venti episodi sono
troppe, e anche il vincitore andrà chiamato indizio. La scheda dirà sempre il numero misurato e mai una
parola come «probabile» se il numero misurato sta sotto il 50%.
