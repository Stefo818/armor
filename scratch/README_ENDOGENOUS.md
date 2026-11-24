# Laboratorio endogeno — uso rapido

Dalla root del repository:

```bash
PYTHONPATH=src python scratch/armor_endogenous_lab.py
```

Il laboratorio è sperimentale e non modifica gli score di produzione. Produce `scratch/armor_endogenous_lab_result.json`.

## Cosa testa

Campiona le ultime sedute mensili entro il 5% dai massimi a 252 sedute e valuta drawdown futuri di -8%/63 sedute, -10%/126 sedute e -15%/252 sedute. Confronta Logistic Regression L2 e HistGradientBoosting su gruppi di feature separati. Usa walk-forward, baseline di prevalenza del solo training ed embargo specifico per orizzonte.

## Come leggere i risultati

- AUC misura l'ordinamento, non la qualità delle probabilità.
- Brier Skill positivo è necessario ma non sufficiente: verificare calibrazione, PR-AUC, falsi allarmi, recall per episodio e lead-time.
- `episodi_positivi_approssimati` è una stima tramite raggruppamento temporale, non un catalogo ufficiale delle crisi.
- Le serie breadth basate sui componenti correnti non sono ammissibili per la prova primaria.
- Le serie macro FRED sono riviste e non sono veri vintage point-in-time.
- La proxy VWCE usa una serie VT/EURUSD prima della storia effettiva di VWCE; il campione è breve.
- DSR BIS verrà testato solo dopo che l'aggiornamento live avrà popolato `data/series/bis_dsr_*.csv`.

Non utilizzare le probabilità di questo laboratorio come segnali operativi: il suo scopo è far emergere se esiste un vantaggio statistico, non produrre ordini.
