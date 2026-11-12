"""Tabella «Chi ha sbagliato di meno», registro giornaliero in ombra e promozione di FHS+VIX (dati finti, nessuna rete)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from armor import campioni, ombra_modelli as om  # noqa: E402


def _prezzi(n=400, seed=1):
    r = np.random.default_rng(seed).normal(0.0004, 0.01, n)
    return pd.Series(100 * np.exp(np.cumsum(r)), index=pd.bdate_range("2024-01-01", periods=n))


def _pred():
    base = {5: 0.06, 10: 0.04}
    p = {hz: {PR: 0.2} for hz, PR in (("10g", 5), ("1m", 10), ("3m", 10), ("6m", 10))}
    out = {}
    for hz, d in p.items():
        thr = 5 if hz == "10g" else 10
        out[hz] = {"p": {thr: 0.2}, "base": {thr: 0.1}, "sfidante": {"motore": "FHS+VIX", "p": {thr: 0.3}, "div": False, "vix": 20.0}}
    return out


def test_promuovi_rende_fhsvix_principale_e_tiene_a1():
    pred, mid = campioni.promuovi(_pred(), "A1")
    assert mid == "FHS+VIX"
    r = pred["1m"]
    assert r["p"][10] == 0.3 and r["p_a1"][10] == 0.2 and r["motore"] == "FHS+VIX" and abs(r["ratio"] - 3.0) < 1e-9
    # senza sfidante resta tutto com'era
    x = {"1m": {"p": {10: 0.2}, "base": {10: 0.1}}}
    y, m2 = campioni.promuovi(x, "A1")
    assert m2 == "A1" and y["1m"]["p"][10] == 0.2


def test_registro_giornaliero_idempotente(tmp_path, monkeypatch):
    from armor import titan_plus
    monkeypatch.setattr(titan_plus, "oggi", lambda d, p0, pT, p: {hz: v + 0.01 for hz, v in p0.items()})
    monkeypatch.setattr(om, "_titan_ultimo", lambda t: {"10g": 0.11, "1m": 0.07, "3m": 0.2, "6m": 0.3})
    f = tmp_path / "o.csv"
    pred, _ = campioni.promuovi(_pred(), "A1")
    assert om.registra(pred, "2026-11-12", None, path=f) == 4
    assert om.registra(pred, "2026-11-12", None, path=f) == 4
    d = pd.read_csv(f)
    assert len(d) == 4 and set(d.columns) == set(om.COLS)
    r = d[d.hz == "1m"].iloc[0]
    assert abs(r.p_fhsvix - 0.3) < 1e-6 and abs(r.p_a1 - 0.2) < 1e-6 and abs(r.p_titanplus - 0.31) < 1e-6 and abs(r.p_titan - 0.07) < 1e-6


def test_tabella_vincitori_e_colori():
    p = _prezzi()
    dates = p.index[::5][:60]
    righe = []
    rng = np.random.default_rng(3)
    for hz, thr in (("1m", 10),):
        for m, q in (("FHS+VIX", 0.1), ("Titan", 0.1), ("Titan+", 0.1), ("A1", 0.1)):
            for d in dates:
                righe.append({"date": d, "model": m, "hz": hz, "thr": thr, "p": q + (0.2 if m == "A1" else 0.0) + (0.0 if m != "Titan" else 0.001) * rng.random()})
    mp = pd.DataFrame(righe)
    d = om.calcola(p, mp=mp, reg=pd.DataFrame(columns=om.COLS))
    o = d["orizzonti"]["1m"]
    assert [f["nome"] for f in o["finestre"]][:2] == ["Giorno", "Settimana"]
    for f in o["finestre"]:
        assert f["vince"] in ("Pari", "FHS+VIX", "Titan", "Titan+", "A1") and 0 <= f["reale"] <= 1
        assert f["vince"] != "A1" or f["modelli"]["A1"]["err"] <= min(c["err"] for c in f["modelli"].values())
    h = om.html(d)
    assert "hsl(" in h and "Vince" in h and "Titan+" in h
    # colore: scarto zero verde (tinta 120), scarto grande rosso (tinta 0)
    assert om._col(0).startswith("hsl(120") and om._col(0.9).startswith("hsl(0")
