# Protocollo: prova dell'«Indice Unificato» proposto da Gemini (26/11/2026)

Pubblicato PRIMA di calcolare. Proposta: indice = 30% terreno (CAPE, rendimento 10 anni, spread High Yield) + 35% anticipo (stiramento sulle medie a 20 e 50 giorni, VIX su media 60, SKEW) + 35% innesco (VIX/VIX3M, volatilita' a 20 giorni, salto del VIX a 5 giorni); ogni pezzo in percentile mobile a 1260 giorni (minimo 252).

## Adattamenti obbligati (la formula cosi' com'e' non gira sui nostri dati)
- «cape» nell'archivio finisce a settembre 2023: si usa cape_m (mensile, fino a oggi, ritardo 1 mese).
- «hy_oas» ha solo 3 anni (da 11/2023): si usa il differenziale Baa-Treasury 10 anni (baa10y, dal 1986) come spread del credito.
- Dove una serie non esiste ancora (es. VIX3M prima del 07/2006) il percentile vale 50.
- Tutti i dati con 1 giorno di ritardo. Nessun altro cambiamento: pesi, finestre e percentile mobile uguali alla proposta.

## Candidati
- G1: formula di Gemini con gli adattamenti sopra.
- G2: G1 senza il terreno (50% anticipo + 50% innesco), per vedere se il «pavimento strutturale» aiuta o danneggia.
- Riferimento: Indice Crollo attuale.

## Misure (stessi 12 picchi endogeni, selezione = 7 fino al 2011, verifica = 5 dal 2018; mai ritarare dopo)
Ogni punteggio e' portato sulla stessa scala 1-100 dell'indice (percentile crescente dal 1990, stessi tratti) cosi' i numeri sono confrontabili.
1. Stacco: media nelle 10 sedute fino al picco meno la media nei giorni calmi (punti).
2. AUC di giorno: 10 sedute prima del picco contro giorni calmi (per episodio).
3. Reazione: soglia = 95° percentile dei giorni calmi fino al 2007; allarme = primo giorno in [picco-10, picco+40]; protezione = quota di discesa ancora davanti all'allarme (nessun allarme = 0, direzione: piu' alta e' meglio); falsi allarmi = quota di giorni calmi dal 2008 sopra soglia.

## Regola di accettazione (tutte insieme, sulla VERIFICA, rispetto all'attuale)
stacco +5 punti; AUC contro i calmi +0,03; protezione +0,10; falsi allarmi non oltre +1 punto percentuale; e in selezione lo stacco non e' peggiore. Con soli 5 picchi in verifica un passaggio resta «da confermare in avanti».
Esito scritto anche se negativo: ESITO_GEMINI_UNIFICATO.md.
