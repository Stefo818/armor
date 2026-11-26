# Esito: indice Crollo che reagisce in pochi giorni (26/11/2026)

Protocollo: PROTOCOLLO_REAZIONE_RAPIDA.md (commit 502dc30, prima dei calcoli). Script: scratch/reazione_rapida.py; dati: scratch/reazione_rapida_esito.json.

## Due errori miei, dichiarati
1. Nel protocollo la regola (a) e' scritta con il segno al contrario rispetto allo scopo (diceva «discesa residua inferiore di 0,10»; lo scopo e' che l'allarme suoni quando c'e' PIU' discesa ancora davanti). Per non cambiare le regole dopo i numeri, riporto entrambe le letture: lettera e scopo.
2. Nella prima esecuzione lo script dava «nessun allarme = 1» invece di 0 come scritto: corretto subito e rieseguito; i numeri sotto sono quelli corretti.

## Fatto di partenza
Media dell'indice attuale nelle ultime 3/5/10/20 sedute fino al picco: 23,5 / 24,2 / 25,8 / 28,8, contro 22,5 nei giorni calmi. A pochi giorni dal picco l'indice e' quasi indistinguibile dai mercati calmi: i massimi non si preannunciano (in 5 crolli su 12 e' sotto 10 fino al picco).

## Reazione dopo il picco (12 picchi; soglia fissata sul 5% dei giorni calmi fino al 2007)
| candidato | falsi allarmi nei calmi dal 2008 | discesa ancora davanti all'allarme: selezione / verifica | ritardo mediano dal picco (sedute): selezione / verifica |
|---|---|---|---|
| 0 attuale | 5,0% | 0,39 / 0,41 | 10 / 6 |
| 1 veloce (salto e curva del VIX, ribassi a 5 giorni) | 7,3% | 0,52 / 0,61 | 8 / 10 |
| 2 veloce con dati nuovi (VIX9D, VVIX) | 9,1% | 0,63 / 0,74 | 5 / 5 |
| 3 massimo fra attuale e veloce | 0,2% (soglia degenerata, quasi mai suona) | 0,35 / 0,17 | 12 / 14 |

## Verdetto
- Lettura letterale della regola: passa solo il candidato 3, ma perche' non suona quasi mai (protezione minima): un risultato senza senso, e' proprio l'effetto del segno sbagliato.
- Lettura secondo lo scopo: **nessuno passa**. I candidati 1 e 2 danno piu' discesa ancora davanti (+0,20 e +0,33 in verifica) e il 2 suona in media 5 sedute dopo il picco, ma costano troppi falsi allarmi (+2,3 e +4,1 punti percentuali contro il limite di +1).
- **Il candidato 2 (VIX9D e VVIX, dati nuovi) e' il piu' promettente**: reazione in 5 sedute e il 74% della discesa ancora davanti, al prezzo di un allarme falso nei mercati calmi 9 giorni su 100 (contro 5). Va nel registro della prova in avanti, non nell'indice.

## Limiti
12 picchi (5 in verifica); VIX9D esiste dal 2011 e VVIX dal 2007: la parte nuova e' provata su pochi episodi; la soglia e' calibrata sul passato e i falsi allarmi dal 2008 sono piu' alti per tutti i candidati veloci.
