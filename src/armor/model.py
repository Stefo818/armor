"""Modello del rischio di calo: regressioni logistiche semplici sui prezzi S&P 500 (dal 1928)."""
import warnings

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .config import FEATURES, HORIZONS, LEVELS, LOGIT_C, MIN_EVENTS, PRIMARY, TARGETS, VERDICT
from .features import fwd_maxdd, fwd_ret, price_features

warnings.filterwarnings("ignore")


def level_of(ratio: float) -> str:
    for lim, name in LEVELS:
        if ratio < lim:
            return name
    return LEVELS[-1][1]


class Engine:
    """Tiene prezzi, variabili ed esiti futuri. fit(cut) usa SOLO esiti gia' noti alla data cut."""

    def __init__(self, close: pd.Series, feats: list[str] | None = None):
        self.p = close.dropna().astype(float)
        self.feats = feats or FEATURES
        self.F = price_features(self.p)[self.feats].dropna()
        self.dd = {h: fwd_maxdd(self.p, n) for h, n in HORIZONS.items()}
        self.ret = {h: fwd_ret(self.p, n) for h, n in HORIZONS.items()}

    def fit(self, cut: pd.Timestamp) -> dict:
        ip = self.p.index.get_loc(cut)
        fitted = {"cut": cut, "hz": {}}
        for hz, n in HORIZONS.items():
            if ip - n < 0:
                continue
            rows = self.F.index[self.F.index <= self.p.index[ip - n]]
            X = self.F.loc[rows]
            dd, rt = self.dd[hz].loc[rows], self.ret[hz].loc[rows]
            ok = dd.notna() & rt.notna()
            X, dd, rt = X[ok], dd[ok], rt[ok]
            info = {"models": {}, "base": {}, "n": int(len(X))}
            for thr in TARGETS[hz]:
                y = (dd <= -thr / 100).astype(int)
                info["base"][thr] = float(y.mean()) if len(y) else float("nan")
                if y.sum() < MIN_EVENTS or y.nunique() < 2:
                    info["models"][thr] = None
                    continue
                m = make_pipeline(StandardScaler(), LogisticRegression(C=LOGIT_C, max_iter=1000))
                m.fit(X.values, y.values)
                info["models"][thr] = m
            pm = info["models"].get(PRIMARY[hz])
            if pm is not None:
                tp = pm.predict_proba(X.values)[:, 1]
                order = np.argsort(tp)
                info["train_p"] = tp[order]
                info["train_ret"] = rt.values[order]
            fitted["hz"][hz] = info
        return fitted

    def predict(self, fitted: dict, date: pd.Timestamp) -> dict:
        """Stima per tutti gli orizzonti alla data indicata."""
        out = {}
        x = self.F.loc[[date]].values
        for hz, info in fitted["hz"].items():
            probs, base = {}, info["base"]
            for thr, m in info["models"].items():
                probs[thr] = float(m.predict_proba(x)[0, 1]) if m is not None else float(base[thr])
            prim = PRIMARY[hz]
            ratio = probs[prim] / base[prim] if base[prim] > 0 else 1.0
            lev = level_of(ratio)
            res = {"p": probs, "base": base, "ratio": ratio, "level": lev, "verdict": VERDICT[lev]}
            pm = info["models"].get(prim)
            if pm is not None and "train_p" in info:
                tp, tr = info["train_p"], info["train_ret"]
                rank = int(np.searchsorted(tp, probs[prim]))
                half = max(int(0.10 * len(tp)), 50)
                lo, hi = max(0, rank - half), min(len(tp), rank + half)
                w = tr[lo:hi]
                res["ret"] = {"q10": float(np.quantile(w, .10)), "q50": float(np.quantile(w, .50)),
                              "q90": float(np.quantile(w, .90)), "mean": float(w.mean()), "n": int(len(w))}
                sc, lg = pm.named_steps["standardscaler"], pm.named_steps["logisticregression"]
                contrib = lg.coef_[0] * sc.transform(x)[0]
                res["drivers"] = sorted(zip(self.feats, contrib), key=lambda t: -abs(t[1]))
            out[hz] = res
        return out
