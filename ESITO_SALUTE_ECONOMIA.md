# Esito: «Salute dell'economia» calibrata sulle recessioni (25/11/2026)

Protocollo: PROTOCOLLO_SALUTE_ECONOMIA.md (commit b2334ec, scritto prima dei calcoli). Script: scratch/salute_economia.py; dati: scratch/salute_economia_esito.json.

## Risultato
443 mesi (1990-2026), 24 alternative, convalida «lascia fuori una recessione» (4 blocchi).
- **Scelta: E3** = 16 misure con peso uguale (lavoro e produzione 7, PIL USA + area euro 2, famiglie e mutui 7) e una retta calibrata sulla gravità delle recessioni. Costi e tassi esclusi.
- Errore (RMSE) fuori campione: **E3 17,9**; seconda X1 (logistica) 18,1 (entro il 3%, scelta E3 perché più semplice); formula precedente (R0) 49,7; solo pilastro economia (R1) 45,3.
- Regole: (a) RMSE ≤ 0,9×R0: sì · (b) sotto soglia «migliore fra N» 26,7 (mediana dei minimi casuali 27,6): sì · (c) falsi allarmi (indice ≥ 60 in vera espansione) 0%: sì.
- Aggiungere i costi (E4) peggiora molto (RMSE 26,8, AUC 0,74): conferma che gonfiavano il vecchio 88.
- **Oggi (ottobre-novembre 2026): circa 15 su 100** (zona verde). Il vecchio 88 era un percentile: «più alto di quasi tutta la storia», non «vicino a una recessione».

## Limiti dichiarati
- Fuori campione la media nei mesi di recessione forte è solo 58 (la retta a pesi uguali è prudente: nei picchi 2009 e 2020 l'indice completo arriva a ~88, ma nei primi mesi di recessione il PIL arriva in ritardo: settembre 2008 = 48).
- Solo 4 recessioni; PIL con ritardo di 4 mesi e senza revisioni; serie europee su lavoro e produzione ferme al 2023 e quindi escluse; T è una nostra definizione.
- Statistiche per zona: 94% dei giorni sotto 40; zone alte rare (2-3% dei giorni), quindi poco precise.
