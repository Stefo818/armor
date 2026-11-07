"""Validazione walk-forward onesta (dal 2000): usa solo esiti noti alla data di ogni previsione."""
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from .config import (BACKTEST_RET, BASELINE_FEATURES, CALIBRATION, HORIZONS, PRIMARY, RISK_HISTORY, TARGETS,
                     VALIDATION)
from .features import closed_sp500
from .model import Engine


def reliability(auc13: float, bss_all: float, auc_all: float) -> str:
    if auc13 >= 0.65 and bss_all > 0:
        return "Utile"
    if auc_all >= 0.60 and bss_all > 0:
        return "Debole"
    return "Non affidabile"


def run(start: str = "2000-01-01", step: int = 5, refit_every: int = 63) -> pd.DataFrame:
    p = closed_sp500()
    from .autoimprove import champion_engine
    eng = {"armor": champion_engine(p)[0], "semplice": Engine(p, BASELINE_FEATURES)}
    idx = p.index
    last_ok = {hz: idx[-1 - n] for hz, n in HORIZONS.items()}
    test = idx[(idx >= start)][::step]
    recs, hist, btr = [], [], []
    fitted = {k: None for k in eng}
    last_fit_i = -10 ** 9
    for t in test:
        i = idx.get_loc(t)
        if t not in eng["armor"].F.index or t not in eng["semplice"].F.index:
            continue
        if i - last_fit_i >= refit_every:
            fitted = {k: e.fit(t) for k, e in eng.items()}
            last_fit_i = i
        preds = {k: eng[k].predict(fitted[k], t) for k in eng}
        for hz, n in HORIZONS.items():
            if t > last_ok[hz]:
                continue
            for k in eng:
                pr = preds[k].get(hz)
                if pr is None:
                    continue
                for thr in TARGETS[hz]:
                    y = float(eng[k].dd[hz].loc[t] <= -thr / 100)
                    recs.append((t, hz, thr, k, pr["p"][thr], pr["base"][thr], y))
            pa = preds["armor"].get(hz)
            if pa is not None and "ret" in pa and (i % 21 < step):
                real = float(eng["armor"].ret[hz].loc[t])
                btr.append((t.strftime("%Y-%m-%d"), hz, pa["ret"]["q10"], pa["ret"]["q50"], pa["ret"]["q90"], real,
                            real - pa["ret"]["q50"], int(pa["ret"]["q10"] <= real <= pa["ret"]["q90"])))
        row = {"date": t.strftime("%Y-%m-%d")}
        for hz in HORIZONS:
            pa = preds["armor"].get(hz)
            if pa:
                row[f"p_{hz}"] = round(pa["p"][PRIMARY[hz]], 5)
                row[f"base_{hz}"] = round(pa["base"][PRIMARY[hz]], 5)
        hist.append(row)
    d = pd.DataFrame(recs, columns=["date", "hz", "thr", "model", "p", "base", "y"])
    d["yr"] = d["date"].dt.year
    out, cal = [], []
    for (hz, thr, k), g in d.groupby(["hz", "thr", "model"]):
        def bss(m):
            x = g[m]
            return 1 - ((x.p - x.y) ** 2).mean() / ((x.base - x.y) ** 2).mean() if len(x) and x.y.nunique() > 0 else np.nan
        def auc(m):
            x = g[m]
            return roc_auc_score(x.y, x.p) if x.y.nunique() > 1 else np.nan
        allm, early, late = g.yr > 0, g.yr < 2013, g.yr >= 2013
        a_all, a13, b_all = auc(allm), auc(late), bss(allm)
        out.append({"target": f"{hz}_{thr}", "hz": hz, "thr": thr, "model": k, "n": len(g),
                    "base_rate": round(g.y.mean(), 4), "bss_all": round(b_all, 4), "bss_2000_12": round(bss(early), 4),
                    "bss_2013_26": round(bss(late), 4), "auc_all": round(a_all, 3), "auc_2013_26": round(a13, 3),
                    "reliability": reliability(a13, b_all, a_all) if k == "armor" else ""})
        if k == "armor":
            try:
                q = pd.qcut(g.p, 5, duplicates="drop")
                for b, x in g.groupby(q, observed=True):
                    cal.append({"target": f"{hz}_{thr}", "prev": round(x.p.mean(), 4), "real": round(x.y.mean(), 4), "n": len(x)})
            except ValueError:
                pass
    res = pd.DataFrame(out)
    res.to_csv(VALIDATION, index=False)
    pd.DataFrame(cal).to_csv(CALIBRATION, index=False)
    pd.DataFrame(hist).to_csv(RISK_HISTORY, index=False)
    pd.DataFrame(btr, columns=["asof", "horizon", "q10", "q50", "q90", "realized", "discrepancy", "in_range"]).to_csv(BACKTEST_RET, index=False)
    return res
