import json, sys
import numpy as np, pandas as pd
sys.path.insert(0, "scratch")
from armor import store
from classifica_40anni import ESTERNI, MISTE_MAX, PRIMA, finestra
import concentrazione as RC
rng = np.random.default_rng(37); RC.rng = rng
RC.ORIZ = [("T2 63g -8%", 63, 0.08), ("T3 21g -5%", 21, 0.05), ("T5 126g -10%", 126, 0.10)]
sp = store.load("sp500").dropna(); sp = sp[sp.index >= "1971-01-01"]
t = pd.read_csv("data/titan_storia.csv", index_col=0, parse_dates=True); a = t["armor_tarato"].dropna(); cal = a.index
s = sp.reindex(cal).ffill()
mkt = ((s / s.rolling(252, min_periods=126).max() - 1) >= -0.03) & ((s / s.shift(63) - 1) >= 0.03)
M10 = a.rolling(10).mean()

a10 = a.shift(10); da = a - a10
f = lambda x: x.fillna(False).astype(bool)
D1 = f(mkt & ((M10 - M10.shift(42)) >= 6)); D2 = f(mkt & ((M10 - M10.shift(21)) >= 4)); D3 = f(mkt & (M10 >= 45)); V1 = f((da >= 10) & (a < 60))
w = lambda x: x.rolling(21, min_periods=1).max().astype(bool)
S1 = w(D1 | D2); S2 = w(V1); S3 = w(D3)
N = S1.astype(int) + S2.astype(int) + S3.astype(int)
Kc = (N == 0) & ((M10 - M10.shift(42)) < 2)
stati = {"N>=1": N >= 1, "N>=2": N >= 2, "N=3": N >= 3, "K controllo": Kc}
stati = {k: f(v) for k, v in stati.items()}
Y = RC.bersagli(sp).reindex(cal)
fuori = finestra(cal, ESTERNI + ["1973-10-17"])
for d in MISTE_MAX:
    pos = cal.searchsorted(pd.Timestamp(d)); fuori.iloc[max(0, pos - PRIMA):min(len(cal), pos + 180)] = True
ok = (~fuori).to_numpy(); anni = cal.year.to_numpy()
BL = {"1990-2004": anni <= 2004, "2005-2020": (anni >= 2005) & (anni <= 2020)}

res = {"stati": {}, "base_mercato_forte": {}}
kk = stati["K controllo"].to_numpy()
for sn, st in stati.items():
    sa = st.to_numpy().astype(bool)
    r = {"frazione": round(float(sa[ok & (anni <= 2020)].mean()), 3), "episodi_1990_2020": RC.episodi_indip(pd.Series(sa & (anni <= 2020)))}
    for yn in Y.columns:
        y = Y[yn].to_numpy(); rr = {}
        for bn, bm in BL.items():
            d, n, pa, pb = RC.dr(y, sa, ok & bm)
            rr[bn] = {"DR": None if np.isnan(d) else round(float(d), 4), "n": n, "P_dentro": None if pa is None or np.isnan(pa) else round(pa, 4), "P_fuori": None if pb is None or np.isnan(pb) else round(pb, 4),
                      "IC90": RC.ic_dr(y[bm], sa[bm], ok[bm], anni[bm]) if not np.isnan(d) else None}
            if sn != "K controllo":
                d2, *_ = RC.dr(y, sa, ok & bm & (sa | kk)); rr[bn]["DR_vs_K"] = None if np.isnan(d2) else round(float(d2), 4)
        r[yn] = rr
    res["stati"][sn] = r
for yn in Y.columns: res["base_mercato_forte"][yn] = round(float(np.nanmean(Y[yn].to_numpy()[ok & mkt.to_numpy() & (anni <= 2020)])), 4)

import json as _j
for sn, r in res["stati"].items():
    print(sn, "frac", r["frazione"], "ep", r["episodi_1990_2020"])
    for yn in Y.columns:
        print("   ", yn, " | ".join(f"{b} DR {x['DR']} n{x['n']} P{x['P_dentro']}/{x['P_fuori']} ic{x['IC90']} vsK {x.get('DR_vs_K')}" for b, x in r[yn].items()))
n = len(cal); nul = []
for _ in range(500):
    k = int(rng.integers(504, n - 504)); mx = -9
    for sn in ("N>=1", "N>=2"):
        sh = np.roll(stati[sn].to_numpy().astype(bool), k)
        for yn in Y.columns:
            dd, *_ = RC.dr(Y[yn].to_numpy(), sh, ok & BL["2005-2020"])
            if not np.isnan(dd): mx = max(mx, dd)
    nul.append(mx)
print("soglia migliore fra 6", round(float(np.percentile(nul, 95)), 4))
print("oggi N", int(N.iloc[-1]), "N>=2 ultimi anni", {y: round(float((N[cal.year == y] >= 2).mean()), 2) for y in range(2021, 2027)})
json.dump(res, open("scratch/convergenza_esito.json", "w"), indent=1, ensure_ascii=False)
