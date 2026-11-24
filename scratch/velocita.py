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
a10 = a.shift(10); da = a - a10
stati = {"V1 salto": (da >= 10) & (a < 60), "V2 molto rapido": (da >= 15) & (a < 60), "V3 da calma": (da >= 10) & (a10 < 35), "K controllo": (a < 60) & (da >= -3) & (da <= 3)}
stati = {k: v.fillna(False) for k, v in stati.items()}
Y = RC.bersagli(sp).reindex(cal)
fuori = finestra(cal, ESTERNI + ["1973-10-17"])
for d in MISTE_MAX:
    pos = cal.searchsorted(pd.Timestamp(d)); fuori.iloc[max(0, pos - PRIMA):min(len(cal), pos + 180)] = True
ok = (~fuori).to_numpy(); anni = cal.year.to_numpy()
BL = {"1990-2004": anni <= 2004, "2005-2020": (anni >= 2005) & (anni <= 2020)}
res = {"base_mercato_forte": {}, "stati": {}}
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
for yn in Y.columns: res["base_mercato_forte"][yn] = round(float(np.nanmean(Y[yn].to_numpy()[ok & (anni <= 2020)])), 4)
nul = []; n = len(cal)
for _ in range(500):
    k = int(rng.integers(504, n - 504)); mx = -9
    for sn in ("V1 salto", "V2 molto rapido", "V3 da calma"):
        sh = np.roll(stati[sn].to_numpy().astype(bool), k)
        for yn in Y.columns:
            d, *_ = RC.dr(Y[yn].to_numpy(), sh, ok & BL["2005-2020"])
            if not np.isnan(d): mx = max(mx, d)
    nul.append(mx)
res["soglia_migliore_fra_9"] = round(float(np.percentile(nul, 95)), 4)
EV = ["1990-07-16", "1997-10-07", "1998-07-17", "2000-03-24", "2007-10-09", "2010-04-23", "2011-04-29", "2018-01-26", "2022-01-03"]
res["cattura"] = {sn: [d for d in EV if st.iloc[max(0, cal.searchsorted(pd.Timestamp(d)) - 126):cal.searchsorted(pd.Timestamp(d)) + 1].any()] for sn, st in stati.items()}
res["frazione_giorni_stato_2021_2026"] = {sn: round(float(st[cal >= "2021-01-01"].mean()), 3) for sn, st in stati.items()}
# descrittivo 2021-2026: accensioni e cosa e' successo
def inizi(st, gap=126):
    out = []
    for i in np.flatnonzero(st.to_numpy()):
        if not out or i - out[-1] >= gap: out.append(i)
    return out
spc = s
res["episodi_2021_2026"] = {sn: [{"data": str(cal[i].date()), "calo_63g": round(float(spc.iloc[i + 1:i + 64].min() / spc.iloc[i] - 1), 3) if i + 64 < len(cal) else None} for i in inizi(st) if cal[i] >= pd.Timestamp("2021-01-01")] for sn, st in stati.items() if sn != "K controllo"}
res["oggi"] = {k: bool(v.iloc[-1]) for k, v in stati.items()}
json.dump(res, open("scratch/velocita_esito.json", "w"), indent=1, ensure_ascii=False)
print("base mercato forte", res["base_mercato_forte"], "soglia", res["soglia_migliore_fra_9"])
for sn, r in res["stati"].items():
    print(sn, "frac", r["frazione"], "ep", r["episodi_1990_2020"])
    for yn in Y.columns:
        print("   ", yn, " | ".join(f"{b} DR {x['DR']} n{x['n']} P{x['P_dentro']}/{x['P_fuori']} ic{x['IC90']} vsK {x.get('DR_vs_K')}" for b, x in r[yn].items()))
print(res["cattura"]); print(res["frazione_giorni_stato_2021_2026"]); print(json.dumps(res["episodi_2021_2026"])); print(res["oggi"])

pos = [cal.searchsorted(pd.Timestamp(d)) for d in EV]
rng2 = np.random.default_rng(3)
for sn in ("V1 salto", "V2 molto rapido", "V3 da calma"):
    st = stati[sn].to_numpy().astype(bool)
    cnt = lambda x: sum(bool(x[p - 126:p + 1].any()) for p in pos)
    obs = cnt(st); nul = [cnt(np.roll(st, int(rng2.integers(504, n - 504)))) for _ in range(1000)]
    print(sn, "catturati", obs, "su 9; caso", round(np.mean(nul), 2), "p", round(float(np.mean(np.array(nul) >= obs)), 3))
