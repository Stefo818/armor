# -*- coding: utf-8 -*-
"""ESPLORATIVO (non è una prova del protocollo): cosa cambia se i tre segnali «di boom» (prestiti alle imprese, M2, produzione) hanno il segno opposto a quello dichiarato.
Il segno si è visto DOPO i risultati: serve solo a formulare un'ipotesi da verificare in avanti. Eseguire dopo crisi_lente_prova.py."""
import sys, warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
sys.path.insert(0, "src"); sys.path.insert(0, "scratch")
from scipy.stats import rankdata
d = pd.read_pickle("/tmp/terreno/cl.pkl"); ME, ZZ, Y = d["ME"], d["ZZ"].copy(), d["Y"]
GRP = {"cape": "V", "spread_baa_aaa": "K", "prestiti_imprese_g6": "K", "debito_privato_5a": "K", "tasso3m_var12": "L", "curva_10a_3m": "L", "m2_yoy": "L", "tasso_reale": "L", "produzione_g12": "M", "disoccupazione_var12": "M", "inflazione": "M"}
for k in ("prestiti_imprese_g6", "m2_yoy", "produzione_g12"): ZZ[k] = -ZZ[k]
G = pd.DataFrame({g: ZZ[[k for k in ZZ.columns if GRP[k] == g]].mean(axis=1, skipna=True) for g in "VKLM"}); T = G.mean(axis=1, skipna=True).where(G.notna().sum(axis=1) >= 3)
PER = {"retro 1928-1952": ("1928-01-01", "1952-12-31"), "taratura 1953-1989": ("1953-01-01", "1989-12-31"), "conferma 1990-2022": ("1990-01-01", "2022-12-31")}
def auc(s, y):
    s, y = np.asarray(s, float), np.asarray(y, float); ok = np.isfinite(s) & np.isfinite(y); s, y = s[ok], y[ok]; n1 = y.sum(); n0 = len(y) - n1
    return np.nan if n1 < 3 or n0 < 3 else float((rankdata(s)[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))
for tg in ("L", "S", "Q"):
    print("ESPLORATIVO segni invertiti", tg, {p: round(auc(T.values[(ME >= a) & (ME <= b)], Y[tg][(ME >= a) & (ME <= b)]), 2) for p, (a, b) in PER.items()})
def perc(x, minn=120):
    o = np.full(len(x), np.nan)
    for i in range(len(x)):
        h = x[:i + 1]; h = h[np.isfinite(h)]
        if len(h) >= minn and np.isfinite(x[i]): o[i] = (h <= x[i]).mean()
    return o
PT = perc(T.values); AL = PT >= 0.8
for p, (a, b) in PER.items():
    m = (ME >= a) & (ME <= b) & np.isfinite(PT) & np.isfinite(Y["L"]); y = Y["L"][m]; al = AL[m]
    print(p, "sensibilità", round(al[y == 1].mean(), 2) if y.sum() else None, "falsi allarmi", round(al[y == 0].mean(), 2), "n", int(m.sum()))
yl = pd.Series(Y["L"], index=ME); ev = yl[yl == 1].index; eps = []
for x in ev:
    if not eps or (x - eps[-1][-1]).days > 366: eps.append([x])
    else: eps[-1].append(x)
als = pd.Series(AL & np.isfinite(PT), index=ME)
for e in eps:
    w = als[(als.index >= e[0] - pd.DateOffset(months=24)) & (als.index <= e[0])]; on = w[w]
    print("episodio", e[0].date(), "allarme nei 24 mesi prima:", bool(len(on)), "anticipo mesi:", None if not len(on) else int(round((e[0] - on.index[0]).days / 30.4)), "mesi di allarme:", len(on))
