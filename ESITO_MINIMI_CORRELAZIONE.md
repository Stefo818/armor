# Esito: la correlazione aiuta a riconoscere un minimo? (25 novembre 2026)

Protocollo: PROTOCOLLO_MINIMI_CORRELAZIONE.md (commit f7b9de8, scritto prima dei calcoli). Script: scratch/minimi_correlazione.py. Dati: scratch/minimi_correlazione_esito.json. Nessuna regola cambiata dopo i numeri.

## Cosa è stato fatto
Sostituto dichiarato di COR1M: correlazione media a coppie dei 9 settori in 21 sedute (storia dal 1999). COR1M e COR3M veri hanno 3 giorni di archivio: non misurabili. Giorni «sotto stress» (S&P 500 almeno −8% dal massimo dell'anno): 1.311 in scelta (1999-2012), 519 in verifica (2013-2026); blocchi di stress separati: 8 e 11. Bersagli: il minimo regge (T1: nel mese successivo non scende più del 3%; T2: nei tre mesi successivi non scende più del 5%).

## Risultati (AUC: 0,5 = caso)
| punteggio | T1 scelta | T1 verifica | T2 scelta | T2 verifica |
|---|---|---|---|---|
| R0 Occasione (attuale) | 0,559 | 0,567 | 0,525 | 0,589 |
| R1 Svolta (attuale) | 0,577 | 0,531 | 0,574 | 0,546 |
| K1 correlazione che rientra (da sola) | 0,513 | **0,677** | 0,493 | **0,769** |
| K2 correlazione alta (da sola) | 0,485 | 0,573 | 0,560 | 0,704 |
| K3 Occasione + «rientra» | 0,553 | 0,575 | 0,512 | 0,599 |
| K4 Occasione + «alta» | 0,567 | 0,564 | 0,540 | 0,587 |
| K5 Occasione + entrambe | 0,557 | 0,576 | 0,524 | 0,597 |
| K6 Svolta a 6 voci | 0,568 | 0,560 | 0,556 | 0,582 |
Soglia del caso (migliore di 8): T1 0,664, T2 0,759.

**Regole: nessuno passa** (B1 richiede +0,03 su entrambi i bersagli in entrambi i periodi). Resta l'Occasione com'è. Aggiungere la correlazione all'Occasione non cambia nulla (differenze di 0,01).

## Letture
1. **K1 da sola sembra buona solo in verifica** (0,677 e 0,769, appena sopra la soglia del caso) ma in scelta vale 0,51 e 0,49, cioè caso. Un segnale che funziona in un periodo e non nell'altro è, con 8 e 11 blocchi di stress, quasi sicuramente legato a pochi episodi. Non è adottato. È un indizio da riverificare con COR1M/COR3M veri.
2. **L'Occasione attuale distingue poco i minimi che reggono sui singoli giorni** (AUC 0,53-0,59 su questi due bersagli, intervalli larghi). Questa misura non è quella con cui l'Occasione è stata progettata (episodi di calo ≥15%, prova P3); va letta come un limite: sui singoli giorni l'Occasione non è un segnale preciso del fondo.
3. **Il picco di correlazione non coincide con il minimo.** Su 11 discese del 12% o più dal 1999, il picco cade entro ±10 sedute dal minimo di prezzo solo 3 volte su 11. Spesso arriva prima (2002: 26 sedute prima, 2008-09: 64, 2010: 20, 2011: 36, 2022 primo minimo: 49) o dopo (2015: +14, 2018: +12, 2025: +18). Al minimo la correlazione era sopra la sua mediana storica in 10 casi su 11 (unica eccezione: marzo 2022): dice «siamo in zona di stress», non «è il fondo».

## Cosa cambia nell'app
Niente: l'Occasione resta invariata. La correlazione può servire come contesto («tutto scende insieme»), non come segnale di minimo.

## Limiti
Sostituto della correlazione implicita (non COR1M); pochi blocchi di stress; giorni sovrapposti; bersagli scelti prima ma diversi da quelli di progetto dell'Occasione. Si ripete con COR1M/COR3M quando ci saranno almeno due anni di dati veri (si accumulano dal 20 novembre 2026).
