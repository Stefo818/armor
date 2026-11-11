# AGGIORNAMENTO 11/11/2026 — vedi PROTOCOLLO_ARMOR_V47.md
Per decisione dell'utente il motore Titan v47 sostituisce FHS+VIX come riferimento, in due fasi (calcolo giornaliero subito, indice mostrato dopo 10 giorni di verifica). Le regole di revisione annuale (10 novembre 2027) restano. Il testo sotto vale fino al passaggio alla Fase 2.

# Protocollo di revisione dell'Indice Armor (scritto il 10/11/2026, prima di vedere dati nuovi)

Scopo: decidere in anticipo quando e come si possono cambiare l'Indice Armor e i suoi pesi, per non adattarlo al rumore.

## Cosa NON si cambia prima della revisione
- I pesi delle 8 famiglie (22, 18, 8, 12, 12, 8, 6, 14) e le soglie degli indicatori restano fissi fino alla data di revisione.
- Fanno eccezione i **nuovi indicatori**: restano sotto prova automatica con la regola già in vigore (AUC +0,01 in almeno 2 eventi su 3, nessun evento sotto −0,01).

## Quando si rivede
1. **Revisione ordinaria: 10/11/2027** (12 mesi dopo questo protocollo).
2. **Revisione straordinaria: 90 giorni dopo il primo calo dell'S&P 500 di almeno il 10% dal massimo a 252 sedute** (il momento più informativo). La data si registra da sola in `data/scadenze_stato.json`.

## Prova dal vivo (calcolata in automatico, mostrata nella scheda «Verifiche e scadenze»)
Dal 10/11/2026 si contano i giorni il cui esito a 3 mesi è noto e gli eventi di calo ≥10% a 3 mesi. Con almeno 1 evento e 1 non evento si calcola l'AUC dal vivo (riferimento storico: 0,72).

## Regola di decisione (fissata ora)
- I pesi si possono cambiare **solo se** nel periodo dal vivo c'è stato almeno 1 evento di calo ≥10% a 3 mesi. Senza eventi la revisione dei pesi è rinviata di 6 mesi.
- Un nuovo set di pesi diventa ufficiale solo se, con verifica a campione separato (addestramento fino al 2012, prova 2013–oggi): (a) l'AUC a 3 mesi per il calo ≥10% migliora di almeno 0,02 nella prova; (b) non peggiora di più di 0,01 nel periodo dal vivo; (c) la variazione di ogni peso non supera 5 punti.
- Se le condizioni non sono tutte soddisfatte restano i pesi attuali. Il risultato si scrive in questo file, anche se negativo.

## Promemoria
Sono frequenze storiche su pochi episodi indipendenti (circa 4–5 dal 2000). Non è consulenza finanziaria.
