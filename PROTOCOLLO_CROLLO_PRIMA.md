# Protocollo: far salire l'indice Crollo PRIMA dei crolli (26/11/2026)

Scritto e pubblicato PRIMA di calcolare. Richiesta dell'utente: la media dell'indice Crollo nelle sedute prima di un crollo (33,6) e' sotto la media storica (36,1): trovare una soluzione, usando anche i dati nuovi.

## Cosa si misura
- 12 picchi endogeni (PICCHI_ENDOGENI in grafico_indici.py). Selezione = i 7 fino al 2011 (1990, 1997, 1998, 2000, 2007, 2010, 2011); verifica = i 5 successivi (2018 x2, 2022, 2023, 2024). Mai riaddestrare dopo aver visto la verifica.
- Finestra «prima»: le 20 sedute fino al picco incluso. Giorni «calmi»: come nella scheda (a meno del 5% dal massimo e nessun calo >5% nelle 63 sedute dopo).
- Metrica 1 (la richiesta): stacco = media dell'indice nelle 20 sedute prima del picco (ogni crollo pesa uno) meno la media nei giorni calmi, in punti dell'indice (0-100, scala identica per tutti i candidati: percentile atteso dello stesso punteggio).
- Metrica 2 (onesta): AUC a livello di giorno, finestre «prima» contro giorni calmi, e contro tutti i giorni; 0,5 = caso.
- Controllo: la media dell'indice nei giorni calmi non deve salire piu' di 3 punti rispetto a oggi (altrimenti si «vince» solo alzando tutto).

## Candidati (fissati ora, nessun altro dopo)
0. Indice attuale (versione 2).
1. Attuale 70% + volatilita' recente (VIX sopra la sua media a 60 giorni, in percentile) 30%.
2. Attuale 70% + ampiezza media giornaliera 5 su 60 giorni (in percentile) 30%.
3. Attuale 70% + stress dei titoli di Stato europei (dato nuovo: bce_sov_area_euro_pesata, livello e variazione a 20 giorni, percentile) 30%.
4. Attuale 70% + contributi CISS (dato nuovo: media dei percentili di bce_ciss_contr_banche, _monetario, _azioni, _obbligazioni, _cambi) 30%.
5. Attuale 55% + 1, 2, 3 ciascuno 15%.
Trattamento dei dati nuovi: ritardo di 1 giorno; prima del 2000 il componente vale 50 (neutro).

## Regola di accettazione (tutte insieme)
Un candidato sostituisce l'attuale solo se, sulla VERIFICA (5 picchi): stacco maggiore dell'attuale di almeno 5 punti E AUC contro i giorni calmi maggiore di almeno 0,03 E media nei giorni calmi non oltre +3 punti. In piu' lo stacco in selezione non deve essere peggiore dell'attuale. Con soli 5 episodi di verifica, anche se passa, resta «da confermare in avanti» e si registra nel registro delle prove in avanti.

## Cosa si fa comunque
Qualunque sia l'esito, si corregge il confronto nella scheda: il termine giusto per «Prima di un crollo» e' il giorno calmo, non la media storica (che include le fasi di discesa gia' avviate).
Esito scritto anche se negativo: ESITO_CROLLO_PRIMA.md.
