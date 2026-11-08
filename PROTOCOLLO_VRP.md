# PROTOCOLLO DELL'ESPERIMENTO VRP E HAR — versione 1, datato 8 novembre 2026

Scritto **prima** di calcolare qualsiasi risultato (PIANO_ARMOR3 Fasi 6a e 6b). Non cambia dopo aver visto i risultati. L'impronta di questo file va in `data/protocollo_log.csv`.
Stato dell'esperimento: **ombra**. Non può diventare riferimento ufficiale con questo protocollo: le varianti ammesse all'adozione sono solo le 12 di PROTOCOLLO_VERIFICA.md §3.
Un'eventuale adozione richiede un protocollo nuovo (versione 2), con più dati, e la verifica storica dell'articolo §4 di PROTOCOLLO_VERIFICA.md.

## Dati e limite dichiarato
- Apertura, massimo, minimo e chiusura di ^GSPC (Yahoo). **Controllo di qualità fatto prima dell'esperimento**: fino al 2005 l'apertura coincide con la chiusura del giorno prima in oltre il 93% dei giorni
  (Yahoo non ha l'apertura vera dell'indice in quegli anni); nel 2008-2010 la coincidenza è 1-2%. L'esperimento usa quindi solo dal **2008-01-01** (anche l'indice VIX a 6 mesi parte nel 2008). Previsioni valutate ogni 5 sedute dal 2011-01-03.
- Il campione è corto (circa 15 anni, 6 episodi di calo ≥10% in un mese): i risultati valgono come indizio, non come prova.

## Grandezze
- Stimatore Yang-Zhang su 21 sedute (separa la parte notturna da quella di seduta); proxy giornaliero v = (log apertura/chiusura precedente)² + Rogers-Satchell. Varianza annualizzata in %² (come VIX²).
- Esito della previsione di varianza: varianza realizzata Yang-Zhang nelle 21 sedute successive.
- Regressioni sempre walk-forward: per prevedere alla data d si usano solo date con esito noto (d' ≤ d − 21), a partire da 750 osservazioni, previsione limitata sotto a 25 %² (5% di volatilità).

## Modelli (stessi numeri casuali, controllo delle code T1, 3.000 percorsi, seme fisso per data)
1. **VIX**: varianza attesa a 21 sedute = VIX².
2. **FHS**: V0T1 (nessun dato di opzioni).   3. **FHS+VIX**: V1T1 (peso 0,5, premio 0,8) — è il riferimento del confronto.
4. **HAR**: regressione della varianza realizzata futura su proxy giornaliero, media settimanale e Yang-Zhang a 21 sedute (HAR-RV).
5. **HAR-X**: HAR più VIX² (il coefficiente su VIX² misura quanto del premio di volatilità è informativo).
6. **FHS+VIX+VRP**: varianza attesa = VIX² − VRP stimato ex ante, con VRP = media delle ultime 1.260 differenze (VIX² − varianza realizzata successiva) già note; limitata sotto a 0,25·VIX².
Per i modelli 1, 4, 5, 6 la varianza iniziale del GARCH è scelta perché la media attesa dei primi 21 giorni coincida con la previsione (come in V2).

## Metriche e decisione
- Varianza: QLIKE della previsione a 21 sedute contro la realizzata Yang-Zhang, differenza contro il VIX con test di Diebold-Mariano (HAC) e Holm.
- Probabilità, stessi esiti per tutti: calo ≥5% da oggi in 1 mese, drawdown ≥5% in 1 mese, calo ≥10% in 3 mesi, chiusura in negativo a 1 e a 3 mesi. Brier, BSS, pendenza di calibrazione, differenza di Brier contro FHS+VIX (bootstrap al 90%, DM con Holm su 5 confronti).
- Distribuzione: copertura della fascia 10-90 e CRPS del rendimento a 1 e 3 mesi.
- Esito: un modello «promettente» se la differenza di Brier contro FHS+VIX ha intervallo tutto a favore su almeno 3 dei 5 esiti con Holm < 0,10. Altrimenti si scrive «nessun vantaggio dimostrato». In ogni caso resta in ombra.
- Ogni prova è nel registro (`tipo = vrp1`), anche se negativa.
