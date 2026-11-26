# Esito, giro 1: Indice Crollo versione 3 appreso dai dati (26/11/2026)

Protocollo: PROTOCOLLO_CROLLO_V3.md (commit 00df00f). Script: scratch/crollo_v3.py; dati: scratch/crollo_v3_esito.json. Dieci candidati, addestrati a finestra crescente dal 2001 (fuori campione), scelta 2001-2014, verifica dal 2015. Soglia del caso (AUC su Ya, 2015+): 0,588.

## Risultato: nessun candidato passa (vincitore in scelta: C4, alberi su F1, bersaglio ab; fallisce tutti e cinque i criteri)
AUC in verifica (Ya calo del 4% in 10 sedute / Yb calo profondo): vecchio 0,704 / 0,820; Gemini 0,653 / 0,652; i dieci modelli appresi 0,661-0,696 / 0,760-0,825. Stacco prima-picco (crolli 2018-2024) meno giorni calmi: vecchio -2,3; modelli appresi tra -5,7 e 0,0; Gemini +8,1.
In scelta (2001-2014) i modelli appresi sono migliori del vecchio (punteggio 0,82-0,87 contro 0,80), ma questo vantaggio non si ripete dal 2015: tipico di un adattamento al passato.

## Cosa si impara
1. Un modello che impara «calo nei prossimi giorni» converge sul comportamento del vecchio indice: bravo a riconoscere la tensione in corso, non si alza prima dei picchi (stacco ~0 o negativo).
2. Aggiungere le parti di Gemini (F1) o i dati nuovi (F2: VIX9D, VVIX, CISS, titoli di Stato europei, fattori Fama-French, dispersione dei settori) non migliora in verifica: C5-C8 non battono C9-C10 (solo le vecchie famiglie, riponderate).
3. Il bersaglio sbagliato produce l'indice sbagliato: per alzare l'indice PRIMA dei picchi bisogna insegnargli proprio quello (giro 2).
