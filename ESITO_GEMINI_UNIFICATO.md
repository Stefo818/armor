# Esito: «Indice Unificato» proposto da Gemini (26/11/2026)

Protocollo: PROTOCOLLO_GEMINI_UNIFICATO.md (commit 410948c, prima dei calcoli). Script: scratch/gemini_unificato.py; dati: scratch/gemini_unificato_esito.json.
Adattamenti obbligati (dichiarati nel protocollo): «cape» finisce a settembre 2023 → cape_m; «hy_oas» ha 3 anni → baa10y (dal 1986); VIX3M dal 2006 (50 prima). La formula cosi' com'e' non gira sui nostri dati.

## Risultati (12 picchi endogeni, 10 sedute fino al picco; scala 1-100 dell'indice per tutti)
| | attuale | G1 (Gemini) | G2 (senza terreno) |
|---|---|---|---|
| media nei giorni calmi | 22,5 | 35,5 | 35,8 |
| stacco prima-picco meno calmi: selezione (7) / verifica (5) | +12,5 / **-7,8** | +9,6 / **+8,9** | +2,8 / +3,8 |
| AUC contro i giorni calmi: selezione / verifica | 0,585 / 0,411 | 0,608 / 0,628 | 0,541 / 0,568 |
| discesa ancora davanti all'allarme: selezione / verifica | 0,39 / 0,41 | 0,51 / 0,62 | 0,55 / 0,48 |
| ritardo mediano dal picco, verifica (sedute) | 6 | 3 | 15 |
| falsi allarmi nei calmi dal 2008 | 5,0% | 4,6% | 6,9% |
Media delle 10 sedute prima del picco, G1, per crollo: 1997 62,9; 1998 58,8; 2000 67,3; 2007 56,8; 2010 17,3; 2011 7,3; 2018 (gen) 61,2; 2018 (set) 54,7; 2022 37,0; 2023 24,9; 2024 43,8.

## Verdetto secondo la regola scritta prima
**Non accettato per un solo criterio**: in selezione lo stacco di G1 (+9,6) e' peggiore dell'attuale (+12,5). Gli altri quattro criteri sulla verifica sono rispettati: stacco +16,7 punti sull'attuale, AUC +0,22, protezione +0,21, falsi allarmi -0,4 punti percentuali.

## Cosa si legge, senza farsi illusioni
- E' la **prima formula, fra tutte quelle provate, che alza davvero l'indice nei giorni prima dei crolli recenti** (2018, 2018, 2022, 2023, 2024: da 3-15 a 25-61) e che reagisce in 3 sedute dal picco con il 62% della discesa ancora davanti, senza piu' falsi allarmi.
- Il merito sembra venire dal **terreno** (CAPE, rendimento a 10 anni, credito): senza di esso (G2) il vantaggio sparisce. Ma negli anni 2018-2024 CAPE e rendimenti erano alti per tutti i giorni: l'indice parte da piu' in alto anche nei mercati calmi (media dei calmi 35,5 contro 22,5), quindi parte del guadagno puo' essere un effetto del livello di quegli anni e non una capacita' di avvisare. Per questo la regola chiede coerenza anche in selezione, dove e' peggiore.
- Non anticipa i crolli del 2010 e 2011 (17,3 e 7,3): i massimi da mercato calmo restano invisibili.
- Verifica su soli 5 picchi: il margine d'errore e' grande.
- Le frasi del testo di Gemini sui numeri non sono confermate dai nostri dati: l'AUC 0,77 delle varianti V4/N4 era sul calo del 3% in 5 giorni da giorni calmi, con miglioramento +0,009 (dentro il rumore); «anticipa di 3-15 sedute» non e' stato misurato in quella forma.

## Decisione
Non si sostituisce l'indice Crollo. G1 va nel registro in avanti (data/indizi_registro.csv: crollo_unificato e crollo_unificato_allarme, soglia 64,2). Fra 6 mesi si decide: se in avanti regge il vantaggio, puo' diventare un secondo indice o il nuovo Crollo.
