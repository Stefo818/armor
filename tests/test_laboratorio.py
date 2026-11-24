import numpy as np
import pandas as pd

from armor import laboratorio as L


def _prezzi(n=1200, seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2026-11-24", periods=n)
    return pd.Series(100 * np.cumprod(1 + rng.normal(0.0003, 0.01, n)), index=idx)


def test_in_attesa_senza_giorni():
    px = _prezzi()
    reg = pd.DataFrame({"data": ["2026-11-23"], **{k: [1] for k, *_ in L.IPOTESI}})
    v = L.valuta(reg, px)
    assert all(x["verdetto"] == "in attesa" for x in v.values())


def test_in_attesa_con_pochi_episodi():
    px = _prezzi(); n = 300
    reg = pd.DataFrame({"data": [str(d.date()) for d in px.index[:n]]})
    for k, *_ in L.IPOTESI:
        reg[k] = 0
    reg.loc[:10, "v1"] = 1
    v = L.valuta(reg, px)
    assert v["v1"]["verdetto"] == "in attesa" and "episodi" in v["v1"]["motivo"]


def test_stato_calcolabile_e_senza_futuro():
    rng = np.random.default_rng(2)
    idx = pd.bdate_range("2015-01-01", periods=800)
    a = pd.Series(40 + np.cumsum(rng.normal(0, 1, 800)), index=idx)
    px = pd.Series(100 * np.cumprod(1 + rng.normal(0.0004, 0.01, 800)), index=idx)
    s1 = L.stati(a, px)
    s2 = L.stati(a.iloc[:600], px.iloc[:600])
    assert set(s1.columns) == {"v1", "d2", "calma", "n"}
    assert (s1.iloc[:600].to_numpy() == s2.to_numpy()).all()   # nessuna informazione dal futuro


def test_terreno_semaforo():
    assert L.terreno({"bolla_rosso": 1, "calma": 1})["stato"] == "rosso"
    assert L.terreno({"calma": 1})["stato"] == "verde"
    t = L.terreno({"calma": 0, "n": 1})
    assert t["stato"] == "neutro" and "consiglio" not in t["frase"].lower().replace("non è un consiglio", "")
    assert "vendere" not in L.terreno({"calma": 1})["frase"].lower()
