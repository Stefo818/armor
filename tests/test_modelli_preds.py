import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from armor import modelli_preds as mp  # noqa: E402


def test_archivio_previsioni_per_modello(tmp_path, monkeypatch):
    monkeypatch.setattr(mp, "FILE", tmp_path / "m.csv")
    d = pd.DataFrame({"date": pd.bdate_range("2020-01-01", periods=4), "hz": ["1m", "1m", "3m", "3m"], "kind": "down", "thr": [10, 5, 10, 15], "p": [0.1, 0.2, 0.3, 0.4]})
    assert mp.salva("Titan", d) == 2          # solo le soglie principali (1m 10%, 3m 10%)
    assert mp.salva("FHS", d) == 4            # l'altro modello si aggiunge
    assert mp.salva("Titan", d) == 4          # rifare Titan non duplica
    c = mp.carica()
    assert set(c.model) == {"Titan", "FHS"} and len(c) == 4
