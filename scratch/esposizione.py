import json, sys
import numpy as np, pandas as pd
from armor import store
TAX, COST = 0.26, 0.0015
sp = store.load("sp500").dropna()
t = pd.read_csv("data/titan_storia.csv", index_col=0, parse_dates=True)
A = t["armor_tarato"].dropna(); cal = A.index
px = sp.reindex(cal).ffill(); r = px.pct_change().fillna(0).to_numpy()
def target(a, th, e):
    """esposizione a fine giorno i (decisa con A[i]); applicata il giorno dopo"""
    tg = np.ones(len(a)); cur = 1.0
    for i, v in enumerate(a):
        if cur == 1.0 and v >= th: cur = e
        elif cur != 1.0 and v < th - 5: cur = 1.0
        tg[i] = cur
    return tg
def sim(r, tg):
    n = len(r); V = 1.0; C = 0.0; B = 1.0; cur = 1.0; w = np.empty(n); ntr = 0
    for i in range(n):
        V *= 1 + r[i]
        if i > 0 and tg[i - 1] != cur:
            tot = V + C; want = tg[i - 1] * tot
            if want < V:
                s = V - want; g = max(s * (1 - B / V), 0); C += s - TAX * g - COST * s; B -= s * B / V; V -= s
            else:
                b = want - V; C -= b; V += b * (1 - COST); B += b
            cur = tg[i - 1]; ntr += 1
        w[i] = V + C
    liq = V + C - TAX * max(V - B, 0)
    return w, liq, ntr
def stats(w, liq, idx):
    yrs = (idx[-1] - idx[0]).days / 365.25; cagr = (liq) ** (1 / yrs) - 1
    dd = (w / np.maximum.accumulate(w) - 1).min(); return {"finale_netto": round(float(liq), 3), "cagr": round(float(cagr), 4), "maxdd": round(float(dd), 4), "calmar": round(float(cagr / abs(dd)), 3)}
def esegui(a_, r_, idx, combos):
    bh = stats(*sim(r_, np.ones(len(r_)))[:2], idx); out = {}
    for th, e in combos:
        w, liq, ntr = sim(r_, target(a_, th, e)); s = stats(w, liq, idx); s["operazioni"] = ntr; out[f"{th}/{int(e*100)}%"] = s
    return bh, out
combos = [(th, e) for th in (55, 60, 65, 70) for e in (0.5, 0.0)]
m1 = cal <= "2012-12-31"; m2 = cal >= "2013-01-01"; m3 = cal >= "2024-01-01"
a = A.to_numpy()
bh1, o1 = esegui(a[m1], r[m1], cal[m1], combos)
best = max(o1, key=lambda k: o1[k]["calmar"]); th, e = int(best.split("/")[0]), int(best.split("/")[1][:-1]) / 100
print("SCELTA 1990-2012: BH", bh1); [print(" ", k, v) for k, v in o1.items()]; print("scelta", best)
bh2, o2 = esegui(a[m2], r[m2], cal[m2], combos); print("VERIFICA 2013-2026: BH", bh2); [print(" ", k, v) for k, v in o2.items()]
bh3, o3 = esegui(a[m3], r[m3], cal[m3], [(th, e)]); print("2024-2026 (pulito) BH", bh3, o3)
# rumore: segnale spostato, tutte le varianti, si tiene la migliore (differenza di calmar vs BH) su 2013-2026
rng = np.random.default_rng(11); dif = bh2["calmar"]; n = len(a); nul = []
for _ in range(200):
    k = int(rng.integers(504, n - 504)); sh = np.roll(a, k)[m2]
    _, o = esegui(sh, r[m2], cal[m2], combos); nul.append(max(v["calmar"] for v in o.values()))
soglia = float(np.percentile(nul, 95)); print("calmar scelta", o2[best]["calmar"], "soglia rumore 95", round(soglia, 3), "BH", bh2["calmar"])
res = {"scelta": best, "bh_scelta": bh1, "varianti_scelta": o1, "bh_verifica": bh2, "verifica": o2, "pulito_2024_26": {"bh": bh3, "regola": o3}, "soglia_rumore": round(soglia, 3)}
json.dump(res, open("scratch/esposizione_esito.json", "w"), indent=1)
# grafico di cassa: scarto percentuale in giorni 'esposto ridotto'
tg = target(a, th, e); print("quota giorni ridotti 1990-2026", round(float((tg < 1).mean()), 3), "oggi", tg[-1], "indice", a[-1])
