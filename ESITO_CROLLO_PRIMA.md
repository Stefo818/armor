# Esito: far salire l'indice Crollo prima dei crolli (26/11/2026)

Protocollo: PROTOCOLLO_CROLLO_PRIMA.md (commit 3d28fbb, prima dei calcoli). Script: scratch/crollo_prima.py; dati: scratch/crollo_prima_esito.json. Sei candidati (indice attuale, + volatilita', + ampiezza, + titoli di Stato europei [dato nuovo], + contributi CISS [dato nuovo], misto).

## Risultato: nessun candidato passa la regola di accettazione.
Media dell'indice nelle 20 sedute prima del picco (12 crolli nati dentro la finanza) e nei giorni calmi:
- Indice attuale: calmi 22,5; selezione (7 crolli fino al 2011) 39,0; verifica (5 crolli dal 2018) 17,3; tutti 29,1. Stacco sui giorni calmi: +16,4 in selezione, **-5,3 in verifica**.
- Volatilita' recente: stacco verifica -4,4; ampiezza: -3,1; misto: -5,0 (e alzano la media dei calmi di 3 punti: peggiorano).
- Titoli di Stato europei (dato nuovo): selezione 41,9 (meglio), verifica 15,8, stacco -8,1.
- CISS contributi (dato nuovo): selezione 45,7 (stacco +24,9, AUC 0,78), verifica 19,6, stacco -1,2, AUC 0,475. Il migliore, ma sulla verifica non separa dal caso.
- Per crollo (indice attuale, media 20 sedute prima): 1997 69,9; 1998 45,0; 2000 75,1; 2007 35,5; 2010 2,2; 2011 6,0; 2018 (gennaio) 3,0; 2018 (settembre) 9,4; 2022 22,0; 2023 43,9; 2024 7,9.

## Cosa significa
1. Il numero 33,6 e' piu' alto dei mercati calmi (22,5): l'indice prima di un crollo e' in media +11 punti sopra i giorni tranquilli. Il confronto con la media storica (36,1) inganna: quella media comprende le fasi di discesa gia' avviate, quando l'indice e' altissimo per definizione.
2. I crolli partiti da mercato calmo (2010, 2011, 2018, 2024) lasciano l'indice a 2-9: nessuna delle misure provate, nuove comprese, li vede in anticipo. Alzare la media «a forza» (pesi scelti guardando quei crolli) darebbe un indice alto anche nei mercati calmi e non aumenterebbe la capacita' di avvisare: sarebbe un'illusione costruita sul passato.
3. Le misure che si illuminano prima di un crollo lento (1997-2000, 2007, 2022, 2023) restano quelle gia' presenti; il miglioramento in selezione dei dati nuovi (CISS: +8 punti di stacco, AUC 0,78) non regge sulla verifica.

## Cosa si e' cambiato
Solo il testo della scheda: la tessera «Media storica» dice che comprende le discese gia' in corso, e «Prima di un crollo» riporta il confronto con i mercati calmi (in punti). Indice invariato. Da rifare quando saranno accumulati i dati nuovi in avanti (Cboe a breve scadenza, VVIX, DTCC): ripetere la prova dopo almeno 6 mesi.
