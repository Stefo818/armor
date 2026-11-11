"""Test del motore Titan con dati finti (nessuna rete, nessun dato vero)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from armor import titan  # noqa: E402


def _raw(n=4200, seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2005-01-03", periods=n)
    S = {}
    px = lambda start, vol: pd.Series(start * np.exp(np.cumsum(rng.normal(0.0003, vol, n))), index=idx)
    for k in ["sp500", "rsp", "iwm", "dax", "n225", "eem", "gold", "copper", "hyg", "ief", "kre", "iyt", "smh",
              "xlk", "xlf", "xlv", "xly", "xli", "xlp", "xle", "xlu", "xlb"]:
        S[k] = px(100.0, 0.01)
    S["dxy"], S["oil"] = px(90.0, 0.005), px(60.0, 0.02)
    S["vix"] = pd.Series(np.clip(18 + np.cumsum(rng.normal(0, 0.6, n)) % 25, 10, 60), index=idx)
    S["vix3m"], S["vvix"], S["skew"] = S["vix"] * 1.05, S["vix"] * 5, pd.Series(125 + rng.normal(0, 5, n), index=idx)
    S["y3m"], S["y5y"], S["y10y"] = [pd.Series(v + rng.normal(0, 0.05, n).cumsum() * 0.02, index=idx) for v in (1.0, 2.0, 3.0)]
    m = pd.date_range(idx[0], periods=n // 21, freq="MS")
    for k in ["permit", "indpro", "cpi", "cp"]:
        S[k] = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.002, 0.01, len(m)))), index=m)
    S["cape"], S["pe"], S["ps"] = (pd.Series(v + rng.normal(0, 1, len(m)), index=m) for v in (25.0, 20.0, 2.0))
    S["hy_oas"] = pd.Series(4 + rng.normal(0, 0.5, n).cumsum() * 0.02, index=idx)
    S["nfci"] = pd.Series(rng.normal(0, 0.3, n), index=idx)
    S["icsa"] = pd.Series(250000 + rng.normal(0, 8000, n).cumsum() % 50000, index=idx)
    S["walcl"], S["tga"], S["rrp"] = (pd.Series(v, index=idx) for v in (8e6, 5e5, 1e3))
    return S


def _build(S):
    return titan.build_titan(titan.build_features(titan.market_stage(S)))


def test_scala_e_colonne():
    df = _build(_raw())
    for c in ["armor_index", "super_armor_index", "lost_decade_radar", "p1_stress", "p6_stress"]:
        assert df[c].between(1, 100).all(), c
        assert df[c].notna().all(), c
    assert set(titan.REQUIRED_COLS) <= set(df.columns)


def test_nessun_dato_dal_futuro():
    S = _raw()
    full = _build(S)
    for cut in [2500, 3300]:
        sub = {k: v.loc[:full.index[cut]] for k, v in S.items()}
        d2 = _build(sub)
        t = d2.index[-1]
        for c in ["armor_index", "super_armor_index"]:
            assert abs(d2[c].iloc[-1] - full.loc[t, c]) < 1e-6, (c, t)


def test_clean_series_senza_bfill():
    s = pd.Series([np.nan, np.nan, 5.0, np.nan])
    assert list(titan.clean_series(s, -1.0)) == [-1.0, -1.0, 5.0, 5.0]


def test_previsioni_oggi_forma():
    df = _build(_raw())
    r = titan.walk_forward(df, 126, 0.10, include_today=True, step=60)
    assert 0.0 <= r["p_dd_v40"].iloc[-1] <= 1.0
    assert 0.0 <= r["p_up_v40"].iloc[-1] <= 1.0
    assert r.index[-1] == df.index[-1]
