import pandas as pd
from armor import status_index as si


def test_mappa_tratti_estremi_e_monotona():
    import numpy as np
    idx = pd.date_range("1990-01-02", periods=800, freq="B")
    s = pd.Series(np.linspace(0, 1, 800), index=idx)
    m = si.mappa_tratti(s).dropna()
    assert len(m) > 0 and m.min() >= 1 and m.max() <= 100
    assert m.is_monotonic_increasing


def test_livello_fasce():
    assert si.livello("stato", 10) == 0
    assert si.livello("stato", 90) == 4


def test_leggi_struttura():
    d = si.leggi()
    if d:
        for k in ("crollo", "minimi", "stato"):
            assert 1 <= d["oggi"][k]["valore"] <= 100
            assert "tendenza" in d["oggi"][k]


def test_quadro_sette_valori():
    from armor import quadro
    h = quadro.html()
    for k in ("armor", "super", "crollo", "minimi", "stato", "bolla", "cred"):
        assert f"data-gi='{k}'" in h
    assert "Status index" in h
