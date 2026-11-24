# Esito «Concentrazione del mercato» (24/11/2026)
Segue PROTOCOLLO_CONCENTRAZIONE.md + Emendamento 1, nessuna regola cambiata dopo aver visto i dati. Script: `scratch/concentrazione.py`; numeri completi in `scratch/concentrazione.json`; serie giornaliera (livello, accelerazione, rottura) in `scratch/concentrazione_storia.csv`. 13.989 giorni dal 1971 (1.169 esclusi per cause esterne). I massimi dei tre episodi finanziari classificati prima di misurare (1976, 1980, 1983) coincidono con i massimi reali al giorno.

## Verdetto
**Nessuno stato è «dimostrato».** Soglia del migliore tra 21 test: DR di verifica ≥ 0,42; il massimo ottenuto è 0,22.
1. **Sbilanciamento che accelera (S1)** è un **indizio solo dal 1990**: in 1990-2014 il calo del 5% in un mese avviene nel 42% dei casi contro il 17% (IC90 sopra zero); in 2015-2026 il calo del 12% in tre mesi nel 23% contro il 4% (IC90 sopra zero). Ma i due bersagli non coincidono, gli altri IC includono lo zero, e **prima del 1990 l'effetto è opposto** (1971-1989: 0-3% di cali dopo S1 contro 15-17% fuori, IC90 sotto zero). Su tutta la storia: 15% contro 15%, nessuna differenza.
2. **Il «punto di rottura» con tassi e credito (S3) non si può valutare**: quando la concentrazione accelera, tassi e credito sono quasi sempre calmi (S1 con RT: 0,1% dei giorni, 5 episodi, meno di 30 giorni utili in ogni blocco). L'accelerazione della concentrazione avviene nei rialzi con tassi stabili o in calo, non nelle strette.
3. **L'inversione della leadership (S4)** segnala 8 episodi su 20 ma non anticipa cali a tre mesi (dal 1990 in poi la frequenza dentro lo stato è più bassa che fuori).
4. **La sola rottura di tassi e credito (S7)** funziona meglio di tutta la concentrazione: in 1971-1989 il calo del 5% in un mese 23% contro 12% (IC90 sopra zero), in 1990-2014 36% contro 15% (IC90 sopra zero), in 2015-2026 17% contro 10% (IC include zero). Cattura 6 episodi su 20 con il 13% dei giorni acceso. Segno che il «punto di rottura» è già in tassi e credito, ma si indebolisce nell'ultimo periodo.

## I 13 episodi dello stato S1 (sbilanciato e in accelerazione), per esteso
Calo massimo dei 63 giorni successivi all'inizio, e cosa è successo dopo (descrittivo, non test):
| Inizio | Giorni | Calo max 63g | Nota |
|---|---|---|---|
| 1976-02 | 31 | −0,8% | |
| 1976-12 | 117 | −2,9% | |
| 1979-01 | 29 | −4,9% | |
| 1981-05 | 3 | −6,8% | |
| 1982-11 | 22 | +0,8% | |
| **1998-07** | 69 | **−16,2%** | LTCM; il mercato poi sale fino a marzo 2000 |
| **2015-07** | 23 | **−12,2%** | svalutazione cinese |
| 2017-05 | 7 | −1,3% | falso allarme |
| 2018-03 | 14 | −4,1% | il calo grosso (−19,8%) arriva a settembre, dopo la fine dello stato |
| 2019-04 | 120 | −5,6% | poi pandemia (esterna) |
| 2024-06 | 26 | −4,5% | poi dazi 2025 (esterni) |
| 2025-07 | 17 | −0,1% | falso allarme |
| 2026-05 | 26 | −1,3% | il calo del −11,6% di ottobre 2026 (finanziario) arriva **cinque mesi dopo** |
Lettura onesta: lo stato anticipa spesso, ma con **mesi** di anticipo e senza dire quando; entro 63 giorni funziona in 2-3 casi su 13.

## Valore aggiunto sull'Indice crollo
Dal 1990, nei giorni in cui l'Indice crollo è basso (<41): con S1 acceso il calo dell'8% in tre mesi avviene nel 30% dei casi contro il 7,7% (83 giorni, pochi episodi): è l'unica informazione aggiuntiva trovata, e coincide con ciò che l'utente cerca (indice basso ma mercato fragile). Resta un **indizio** da confermare in avanti.

## Oggi (23/11/2026)
Livello 0,58 (percentile storico), accelerazione 0,43, nessun innesco di rottura acceso, nessuno stato attivo. Proxy più alti: S&P 500 contro mid cap (0,81) e S&P 100 contro S&P 500 (0,73); Nasdaq 100 contro S&P 500 basso (0,29). Il mercato non è «troppo concentrato e in accelerazione» oggi secondo queste misure.

## Limiti
Pesi veri delle singole aziende non disponibili: proxy di prezzo. Pochi episodi (13) e spesso lontani dai cali veri. Orizzonte provato solo fino a 3 mesi: i casi 2018, 2026 suggeriscono un anticipo di 4-6 mesi, **non misurato in questo protocollo** (ipotesi per un protocollo nuovo, da scrivere prima di guardare).

## Cosa entra nell'app
Nulla come allarme. Proposta: scheda informativa «Concentrazione del mercato» (livello, accelerazione, stato, scritta «non dimostrato; indizio dal 1990, anticipo di mesi, non di giorni») e registro giornaliero per la verifica in avanti. In attesa di conferma dell'utente.
