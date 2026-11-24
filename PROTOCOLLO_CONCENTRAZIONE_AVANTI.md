# Protocollo: verifica in avanti del «Sovraccarico del mercato» (4-6 mesi)

Scritto il **24/11/2026**, prima di avere un solo giorno di dati in avanti. Nessuna regola qui sotto si cambia dopo aver guardato i risultati.

## Che cosa si verifica
Il test sul passato (ESITO_CONCENTRAZIONE.md) ha dato solo un **indizio dal 1990**: lo stato «sbilanciato e in accelerazione» (livello ≥ 0,80 e accelerazione ≥ 0,80)
anticipa di mesi, non di giorni; prima del 1990 non funzionava. Qui si guarda se **da oggi in avanti** l'indizio regge.
L'indicatore resta **informativo, peso zero** nel resto dell'app, per tutta la durata della verifica.

## Cosa viene registrato (già attivo)
- `data/concentrazione_registro.csv`: una riga per ogni giorno di Borsa, dal 23/11/2026: S&P 500, sovraccarico (0-100), accelerazione (0-100), z, inversione di guida,
  i quattro segnali di rottura (tassi a 10 anni, banca centrale, credito, condizioni finanziarie), fase, e livello e accelerazione di ciascuno dei sette rapporti.
- `data/concentrazione.json`: stato di oggi e grafico. Le serie dei prezzi usati: `data/series/cn_*.csv`.
- La storia passata si può sempre ricalcolare (`concentrazione.calcola`), ma **non conta come verifica in avanti**.

## Orizzonte e bersagli (fissati ora)
Finestra: dal 23/11/2026 al **23/05/2027** (circa 126 sedute). Valutazione finale: 6 mesi dopo l'ultima accensione, oppure il 23/05/2027 se non si accende nulla.
Bersagli, misurati dalla chiusura S&P 500 del giorno di accensione (minimo nelle 126 sedute successive):
- B1: calo di almeno **8%**; B2: calo di almeno **12%**; B3: calo di almeno **5% entro 84 sedute**.
Riferimenti storici dal 1990, scritti ora (frequenza dei bersagli in un giorno qualunque / in un giorno di stato «sbilanciato e accelera» / in fase di riprezzamento):

| bersaglio | giorno qualunque | stato S1 (301 giorni, 8 episodi) | riprezzamento (379 giorni, 9 episodi) |
|---|---|---|---|
| 126 sedute, −8% | 27,0% | 35,3% | 10,6% |
| 126 sedute, −12% | 18,5% | 26,6% | 1,8% |
| 84 sedute, −5% | 35,7% | 51,2% | 28,8% |

Nota importante: **la fase di riprezzamento non ha mostrato cali forti più frequenti del normale**, anzi meno. Nell'app è presentata come assestamento, non come crollo imminente.

## Regole di giudizio (non negoziabili)
1. Con meno di **6 episodi indipendenti** in avanti non si scrive «dimostrato»: al massimo «coerente», «non coerente» o «insufficiente».
2. Un episodio = un'accensione dello stato S1; due accensioni a meno di 126 sedute sono lo stesso episodio.
3. «Coerente» solo se, per almeno un episodio concluso, almeno due bersagli su tre sono stati raggiunti **e** il calo non cade in una finestra di shock esterno (guerre, pandemie, dazi, geopolitica), da elencare con le fonti. Altrimenti «non coerente» (o «insufficiente» se nessun episodio si è concluso).
4. Se nei 6 mesi lo stato non si accende mai, l'esito è «insufficiente: nessuna accensione», e non si deduce nulla.
5. Controllo continuo, solo descrittivo: correlazione di rango fra sovraccarico del giorno e peggior ritorno nelle 126 sedute successive, sui giorni del registro che hanno finestra completa; intervallo con blocchi mensili. Con ~6 mesi di giorni gli intervalli saranno larghi: non basta da solo per nessuna conclusione.
6. Si registra anche l'esito negativo, scritto in ESITO_CONCENTRAZIONE_AVANTI.md, con data e numeri.

## Cosa NON si fa durante la verifica
- Non si cambiano soglie (0,80), proxy, definizioni degli stati o dei segnali di rottura.
- Non si aggiungono pesi di singole aziende (top 10): richiedono dati a pagamento. Se in futuro si trovano, saranno un test separato con un protocollo nuovo.
- Il Sovraccarico non entra in Indice Armor, Super Armor o Indice crollo.

## Limiti dichiarati
Rapporti fra indici invece dei pesi veri; pochi episodi (8 dal 1990, uno ogni circa 4-5 anni): in 6 mesi è probabile che non se ne chiuda nemmeno uno. Il bersaglio principale è quindi «non peggiorare il giudizio»: raccogliere il registro per riesaminarlo con più dati.
