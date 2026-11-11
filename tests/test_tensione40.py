import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from armor import tensione40 as t  # noqa: E402


def _s(vals):
    return pd.Series(vals, index=pd.bdate_range(end="2026-11-10", periods=len(vals)))


def test_stress():
    m = t.metriche(_s([35.0] * 100 + [46.0] * 40))
    assert m["stato"] == "stress" and m["sopra"] and m["di_fila"] == 40
    assert m["fin"][10]["sopra"] == 10 and abs(m["fin"][10]["media"] - 46.0) < 1e-9
    assert m["fin"][120]["n"] == 120 and m["fin"][120]["sopra"] == 40


def test_ripresa():
    m = t.metriche(_s([33.0] * 100 + [47.0] * 20 + [39.0] * 20))
    assert m["stato"] == "ripresa" and not m["sopra"] and m["di_fila"] == 20
    assert m["fin"][30]["sopra"] == 10


def test_neutro_e_segnale_isolato():
    m = t.metriche(_s([33.0] * 139 + [41.0]))
    assert m["stato"] == "neutro" and m["sopra"] and m["di_fila"] == 1
    assert "isolato" in t.frase(m)
    m2 = t.metriche(_s([33.0] * 140))
    assert m2["stato"] == "neutro" and m2["di_fila"] == 140


def test_poca_storia_e_html():
    assert t.metriche(_s([40.0] * 50)) is None and t.html(None) == ""
    h = t.html(t.metriche(_s(list(np.linspace(30, 50, 140)))))
    assert "sopra 40" in h and "Ultime 120 sedute" in h and "<svg" in h
