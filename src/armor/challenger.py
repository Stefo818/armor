"""Prova, una variabile alla volta, se migliora il modello (regole fissate prima di guardare i risultati).
Regola di adozione per il target principale di ogni orizzonte: miglioramento del Brier skill score > 0,01 sia nel
periodo 2000-2012 sia dal 2013, e AUC piu' alta in entrambi i periodi. Altrimenti la variabile resta solo contesto."""
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from . import store
from .config import DATA, FEATURES, HORIZONS, PRIMARY, TARGETS
from .features import closed_sp500, fwd_maxdd, fwd_ret, price_features
from .model import Engine

CHALLENGERS = DATA / "challengers.csv"
CAPE_TEST = DATA / "cape_test.csv"
CAPE_QUINT = DATA / "cape_quintili.csv"


class E2(Engine):
    """Motore con variabili extra; common = date in cui tutte le variabili sono disponibili."""

    def __init__(self, close, extra=None, common=None):
        self.p = close.dropna()
        self.feats = FEATURES + ([] if extra is None else list(extra.columns))
        F = price_features(self.p)[FEATURES]
        if extra is not None:
            F = F.join(extra)
        F = F.dropna()
        if common is not None:
            F = F.loc[F.index.intersection(common)]
        self.F = F
        self.dd = {h: fwd_maxdd(self.p, n) for h, n in HORIZONS.items()}
        self.ret = {h: fwd_ret(self.p, n) for h, n in HORIZONS.items()}


def _al(s: pd.Series, idx, lag: int, limit: int) -> pd.Series:
    if s.empty:
        return pd.Series(np.nan, index=idx)
    full = s.reindex(pd.date_range(s.index[0], idx[-1])).ffill(limit=limit).shift(lag)
    return full.reindex(idx)


def candidates(idx) -> dict[str, pd.DataFrame]:
    L = lambda k: store.load(k)
    vix, v3 = _al(L("vix"), idx, 0, 5), _al(L("vix3m"), idx, 0, 5)
    baa = _al(L("baa10y"), idx, 1, 5)
    c = {
        "CAPE (valutazioni)": pd.DataFrame({"log_cape": np.log(_al(L("cape_m"), idx, 1, 45))}),
        "NFCI (condizioni finanziarie)": pd.DataFrame({"nfci": _al(L("nfci"), idx, 5, 10)}),
        "Incertezza politica EPU": pd.DataFrame({"log_epu21": np.log(_al(L("epu").rolling(21).mean(), idx, 1, 10))}),
        "VIX": pd.DataFrame({"log_vix": np.log(vix), "vix_chg21": vix / vix.shift(21) - 1}),
        "Curva VIX (VIX3M/VIX)": pd.DataFrame({"vterm": v3 / vix}),
        "SKEW": pd.DataFrame({"skew": _al(L("skew"), idx, 0, 5)}),
        "Spread BAA-10Y": pd.DataFrame({"baa10y": baa, "baa_chg21": baa - baa.shift(21)}),
        "Curva tassi 10Y-3M": pd.DataFrame({"t10y3m": _al(L("t10y3m"), idx, 1, 5)}),
        "Rischio geopolitico GPR": pd.DataFrame({"log_gpr21": np.log(_al(L("gpr").rolling(21).mean(), idx, 1, 10))}),
        "Prezzo/fatturato S&P 500": pd.DataFrame({"log_ps": np.log(_al(L("ps_m"), idx, 1, 100))}),
        "Sentiment AAII (rialzisti meno ribassisti)": pd.DataFrame({"aaii_spread": _al(L("aaii_spread"), idx, 1, 10), "aaii_spread8": _al(L("aaii_spread").rolling(8).mean(), idx, 1, 10)}),
        "Fear & Greed CNN": pd.DataFrame({"fear_greed": _al(L("fear_greed"), idx, 1, 5)}),
        "Ampiezza: titoli sopra media 200g": pd.DataFrame({"breadth200": _al(L("breadth200"), idx, 1, 5)}),
    }
    return c


def _evaluate(A, B, idx, start, step=10, refit=126):
    test = [t for t in idx[(idx >= start)][::step] if t in A.F.index and t in B.F.index]
    last_ok = {hz: idx[-1 - n] for hz, n in HORIZONS.items()}
    recs, fa, fb, lf = [], None, None, -10 ** 9
    for t in test:
        i = idx.get_loc(t)
        if i - lf >= refit:
            fa, fb, lf = A.fit(t), B.fit(t), i
        pa, pb = A.predict(fa, t), B.predict(fb, t)
        for hz in HORIZONS:
            if t > last_ok[hz] or hz not in pa:
                continue
            for thr in TARGETS[hz]:
                recs.append((t, hz, thr, pa[hz]["p"][thr], pb[hz]["p"][thr], pa[hz]["base"][thr],
                             float(A.dd[hz].loc[t] <= -thr / 100)))
    return pd.DataFrame(recs, columns=["t", "hz", "thr", "pa", "pb", "base", "y"])


def _metrics(x):
    if x.y.nunique() < 2 or len(x) < 30:
        return (np.nan,) * 4
    b = lambda c: 1 - ((x[c] - x.y) ** 2).mean() / ((x.base - x.y) ** 2).mean()
    return b("pa"), b("pb"), roc_auc_score(x.y, x.pa), roc_auc_score(x.y, x.pb)


def run() -> pd.DataFrame:
    p = closed_sp500()
    idx = p.index
    rows = []
    for name, ex in candidates(idx).items():
        ok = ex.dropna()
        if len(ok) < 750:
            rows.append({"variabile": name, "target": "", "esito": "storico troppo breve", "n": len(ok)})
            continue
        start = max(pd.Timestamp("2000-01-01"), ok.index[0] + pd.DateOffset(years=12))
        if start > idx[-1] - pd.DateOffset(years=3):
            rows.append({"variabile": name, "target": "", "esito": "storico troppo breve", "n": len(ok)})
            continue
        A, B = E2(p, None, ok.index), E2(p, ex, ok.index)
        d = _evaluate(A, B, idx, start)
        for (hz, thr), g in d.groupby(["hz", "thr"]):
            me, ml, ma = (_metrics(g[g.t.dt.year < 2013]), _metrics(g[g.t.dt.year >= 2013]), _metrics(g))
            dbe, dbl = me[1] - me[0], ml[1] - ml[0]
            dae, dal = me[3] - me[2], ml[3] - ml[2]
            main = thr == PRIMARY[hz]
            if np.isnan(dbe) or np.isnan(dbl):
                esito = "periodo di test troppo breve"
            else:
                esito = "CANDIDATA" if (main and dbe > 0.01 and dbl > 0.01 and dae > 0 and dal > 0) else "scartata"
            rows.append({"variabile": name, "target": f"{hz}_{thr}", "principale": int(main), "n": len(g),
                         "dBSS_2000_12": round(dbe, 4), "dBSS_2013_26": round(dbl, 4),
                         "dAUC_2000_12": round(dae, 3), "dAUC_2013_26": round(dal, 3),
                         "dBSS_tutto": round(ma[1] - ma[0], 4), "test_da": start.strftime("%Y-%m-%d"), "esito": esito})
    out = pd.DataFrame(rows)
    out.to_csv(CHALLENGERS, index=False)
    cape_test(p)
    return out


def cape_test(p: pd.Series) -> None:
    """Il CAPE aiuta a stimare il rendimento a 3, 6, 12, 24 mesi? Confronto fuori campione con la media storica."""
    idx = p.index
    c = np.log(_al(store.load("cape_m"), idx, 1, 45))
    if c.dropna().empty:
        return
    res = []
    for name, h in [("3 mesi", 63), ("6 mesi", 126), ("1 anno", 252), ("2 anni", 504)]:
        r = np.log(p.shift(-h) / p)
        ok = r.notna() & c.notna()
        pairs = []
        for t in idx[(idx >= "2000-01-01") & ok][::21]:
            i = idx.get_loc(t)
            tr = idx[:max(i - h, 0)]
            tr = tr[ok.reindex(tr).values]
            if len(tr) < 1000:
                continue
            b = np.polyfit(c.loc[tr].values, r.loc[tr].values, 1)
            pairs.append((t, r.loc[t], b[0] * c.loc[t] + b[1], r.loc[tr].mean()))
        q = pd.DataFrame(pairs, columns=["t", "real", "pc", "pm"])
        f = lambda g: 1 - ((g.real - g.pc) ** 2).sum() / ((g.real - g.pm) ** 2).sum()
        res.append({"orizzonte": name, "r2_tutto": round(f(q), 3), "r2_2000_12": round(f(q[q.t.dt.year < 2013]), 3),
                    "r2_2013_26": round(f(q[q.t.dt.year >= 2013]), 3), "n": len(q)})
    pd.DataFrame(res).to_csv(CAPE_TEST, index=False)
    r = p.shift(-252) / p - 1
    d = pd.DataFrame({"cape": np.exp(c), "r": r}).dropna()
    d["gruppo"] = pd.qcut(d.cape, 5, labels=False) + 1
    qt = d.groupby("gruppo").agg(cape_mediano=("cape", "median"), rendimento_1a=("r", "mean"),
                                 positivi=("r", lambda x: (x > 0).mean()), p10=("r", lambda x: x.quantile(.1)), n=("r", "size"))
    qt.round(4).reset_index().to_csv(CAPE_QUINT, index=False)
