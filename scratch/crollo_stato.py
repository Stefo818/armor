"""Segue PROTOCOLLO_CROLLO_STATO.md (commit scritto prima dei calcoli)."""
import json, sys
import numpy as np, pandas as pd
sys.path.insert(0, "src"); sys.path.insert(0, "scratch")
from armor import status_index as si, store
from classifica_40anni import ESTERNI, MISTE_MAX
rng = np.random.default_rng(7)
S = si.calcola(); cr, st = S["crollo"], S["stato"]
cal = cr.index; sp = store.load("sp500").dropna().reindex(cal).ffill()
st = st.reindex(cal)
fuori = pd.Series(False, index=cal)
for d in ESTERNI:
    p = cal.searchsorted(pd.Timestamp(d)); fuori.iloc[max(0, p - 63):min(len(cal), p + 61)] = True
for d in MISTE_MAX:
    p = cal.searchsorted(pd.Timestamp(d)); fuori.iloc[max(0, p - 5):min(len(cal), p + 181)] = True
c5 = cr.rolling(5).mean()
X = {"X0 Crollo5": c5, "X1 Stato": st, "X2 prodotto": c5 / 100 * st / 100 * 100,
     "X3 minimo": pd.concat([c5, st], axis=1).min(axis=1),
     "X4 doppia soglia": ((c5 > 60) & (st > 60)).astype(float)}
def minfut(n): return pd.concat([sp.shift(-i) for i in range(1, n + 1)], axis=1).min(axis=1) / sp - 1
B = {"B1 -3% in 5": (minfut(5) <= -0.03), "B2 -8% in 21": (minfut(21) <= -0.08)}
valid = {k: v.astype(float).where(minfut(5 if k.startswith("B1") else 21).notna()) for k, v in B.items()}
def auc(s, y):
    d = pd.concat([s, y], axis=1).dropna(); d.columns = ["s", "y"]
    p, n = d[d.y == 1].s, d[d.y == 0].s
    if len(p) < 5 or len(n) < 5: return np.nan
    r = d.s.rank(); return (r[d.y == 1].sum() - len(p) * (len(p) + 1) / 2) / (len(p) * len(n))
ver = (cal >= "2015-01-01") & ~fuori; sce = (cal <= "2014-12-31") & ~fuori
anni = cal.year
def boot(s, y, mask):
    yy = [a for a in np.unique(anni[mask])]; out = []
    for _ in range(500):
        pick = rng.choice(yy, len(yy)); idx = np.concatenate([np.where((anni == a) & mask)[0] for a in pick])
        out.append(auc(s.iloc[idx], y.iloc[idx]))
    return out
def shuffle(y, mask):
    y2 = y.copy().astype(float); ya = {a: y[(anni == a) & mask].values.astype(float) for a in np.unique(anni[mask])}
    ys = list(ya.values()); perm = rng.permutation(len(ys))
    out = y2.copy()
    for a, j in zip(ya, perm):
        tgt = np.where((anni == a) & mask)[0]; src = ys[j]
        n = min(len(tgt), len(src)); out.iloc[tgt[:n]] = src[:n]
    return out
res = {}
for bn, y in valid.items():
    res[bn] = {}
    for xn, s in X.items():
        res[bn][xn] = {"scelta": auc(s[sce], y[sce]), "verifica": auc(s[ver], y[ver])}
    base = res[bn]["X0 Crollo5"]["verifica"]
    b0 = np.array(boot(X["X0 Crollo5"], y, ver))
    for xn, s in X.items():
        b = np.array(boot(s, y, ver)); d = b - b0
        res[bn][xn]["IC90"] = [float(np.nanpercentile(b, 5)), float(np.nanpercentile(b, 95))]
        res[bn][xn]["diff_vs_X0_IC90"] = [float(np.nanpercentile(d, 5)), float(np.nanpercentile(d, 95))]
    mx = [max(auc(s[ver], shuffle(y, ver)[ver]) for s in X.values()) for _ in range(200)]
    res[bn]["soglia_caso_95"] = float(np.nanpercentile(mx, 95))
    s4 = X["X4 doppia soglia"]; on = ver & (s4 > 0) & y.notna()
    res[bn]["X4_acceso"] = {"giorni": int(on.sum()), "evento_%": float(y[on].mean() * 100) if on.sum() else None, "base_%": float(y[ver & y.notna()].mean() * 100)}
    res[bn]["X0_sopra60"] = {"giorni": int((ver & (c5 > 60) & y.notna()).sum()), "evento_%": float(y[ver & (c5 > 60) & y.notna()].mean() * 100)}
res["oggi"] = {"crollo5": float(c5.iloc[-1]), "stato": float(st.iloc[-1])}
open("scratch/crollo_stato_esito.json", "w").write(json.dumps(res, indent=1, default=float))
print(json.dumps(res, indent=1, default=float))
