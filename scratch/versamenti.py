import json
import numpy as np, pandas as pd
from armor import store
TAX, COST = 0.26, 0.0015
sp = store.load("sp500").dropna()
t = pd.read_csv("data/titan_storia.csv", index_col=0, parse_dates=True)
A = t["armor_tarato"].dropna(); cal = A.index
px = sp.reindex(cal).ffill()
mx = px.rolling(252, min_periods=126).max(); dd = (px / mx - 1).fillna(0)
mn63 = px.rolling(63, min_periods=40).min()
near = (dd > -0.03).to_numpy(); low = (px <= mn63 * 1.01).to_numpy(); deep10 = (dd <= -0.10).to_numpy()
# ---- Parte A descrittiva
fw = (px.shift(-252) / px - 1)
stat = {"vicino ai massimi": near, "nuovi minimi 63g": low, "ribasso>=10%": deep10, "altro": ~(near | low | deep10)}
A_res = {}
for bn, (a, b) in {"1990-2004": ("1990", "2004"), "2005-2020": ("2005", "2020"), "2021-2026": ("2021", "2026")}.items():
    m = (cal >= f"{a}-01-01") & (cal <= f"{b}-12-31") & fw.notna().to_numpy()
    A_res[bn] = {k: {"giorni": int((v & m).sum()), "rend_252g_medio": round(float(fw[v & m].mean()), 4), "mediana": round(float(fw[v & m].median()), 4), "%positivi": round(float((fw[v & m] > 0).mean()), 3)} for k, v in stat.items()}
    A_res[bn]["tutti"] = {"rend_252g_medio": round(float(fw[m].mean()), 4)}
print(json.dumps(A_res, indent=1))
# ---- Parte B
firsts = pd.Series(cal, index=cal).groupby([cal.year, cal.month]).first().to_numpy(); fi = cal.get_indexer(firsts)
sig = {"rib10": deep10, "rib15": (dd <= -0.15).to_numpy(), "min63": low, "armor60": (A >= 60).to_numpy(), "armor70": (A >= 70).to_numpy()}
P = px.to_numpy()
def pac(i0, i1, sg, nr, f):
    """sg: segnale ribasso; nr: vicino ai massimi; indici i0..i1 (mese di versamento)"""
    units = 0.0; cost = 0.0; res = 0.0; paid = 0.0
    for i in fi[(fi >= i0) & (fi <= i1)]:
        paid += 1
        if f == 0 or not nr[i]:
            inv = 1.0
        else:
            inv = 1.0 - f; res += f
        if sg[i] and res > 0:
            extra = min(res, 1.0); inv += extra; res -= extra
        units += inv * (1 - COST) / P[i]; cost += inv
    val = units * P[i1]; tax = TAX * max(val - cost, 0)
    return val - tax + res, paid
def base(i0, i1):
    return pac(i0, i1, sig["rib10"], near, 0)
def run(i0, i1, sg=None, nr=None, combos=None):
    b, paid = base(i0, i1); out = {}
    for sn, s in sig.items():
        for f in (0.5, 1.0):
            v, _ = pac(i0, i1, s, near, f); out[f"{sn}/f{f}"] = round(v / b, 4)
    return b, paid, out
ix = lambda d: int(cal.searchsorted(pd.Timestamp(d)))
i_sel = (0, ix("2012-12-31")); i_ver = (ix("2013-01-01"), len(cal) - 1)
b1, p1, o1 = run(*i_sel); best = max(o1, key=o1.get)
print("SCELTA 1990-2012 piano classico finale", round(b1, 2), "su", p1, "versamenti"); [print(" ", k, v) for k, v in o1.items()]; print("scelta", best, o1[best])
b2, p2, o2 = run(*i_ver); print("VERIFICA 2013-2026", round(b2, 2), p2); [print(" ", k, v) for k, v in o2.items()]
h1 = run(ix("2013-01-01"), ix("2019-12-31"))[2]; h2 = run(ix("2020-01-01"), len(cal) - 1)[2]
print("metà 2013-2019", h1[best], " metà 2020-2026", h2[best])
# rumore
rng = np.random.default_rng(5); nul = []
n = len(cal)
for _ in range(300):
    k = int(rng.integers(504, n - 504)); mxv = 0
    for sn, s in sig.items():
        ss = np.roll(s, k)
        for f in (0.5, 1.0):
            b, _ = pac(*i_ver, ss, np.roll(near, k), 0)
            v, _ = pac(*i_ver, ss, np.roll(near, k), f); mxv = max(mxv, v / b)
    nul.append(mxv)
sogl = float(np.percentile(nul, 95)); print("soglia rumore 95", round(sogl, 4), "scelta in verifica", o2[best])
json.dump({"A": A_res, "scelta": best, "selezione": o1, "verifica": o2, "meta1": h1, "meta2": h2, "soglia": round(sogl, 4)}, open("scratch/versamenti_esito.json", "w"), indent=1)
