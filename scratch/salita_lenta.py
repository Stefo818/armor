import json, sys
import numpy as np, pandas as pd
sys.path.insert(0, "scratch")
from armor import store
from classifica_40anni import ESTERNI, MISTE_MAX, PRIMA, finestra
import concentrazione as RC
rng = np.random.default_rng(31); RC.rng = rng
RC.ORIZ = [("T2 63g -8%", 63, 0.08), ("T3 21g -5%", 21, 0.05)]
sp = store.load("sp500").dropna(); sp = sp[sp.index >= "1971-01-01"]
t = pd.read_csv("data/titan_storia.csv", index_col=0, parse_dates=True); a = t["armor_tarato"].dropna()
cal = a.index
M21, M63 = a.rolling(21).mean(), a.rolling(63).mean()
A = M21.between(37, 45) & ((M21 - M21.shift(42)) >= 4)
B = M63.between(37, 45) & ((M63 - M63.shift(63)) >= 3)
C = A & (M21.rolling(126, min_periods=60).min() <= 33)
K = M21.between(37, 45) & ((M21 - M21.shift(42)) < 1)
stati = {"A": A.fillna(False), "B": B.fillna(False), "C": C.fillna(False), "K controllo": K.fillna(False)}
Y = RC.bersagli(sp).reindex(cal)
fut = pd.concat([a.shift(-i) for i in range(1, 43)], axis=1).max(axis=1); T1 = (fut >= 60).astype(float); T1[a.shift(-42).isna()] = np.nan
Y.insert(0, "T1 indice>60 in 42g", T1)
fuori = finestra(cal, ESTERNI + ["1973-10-17"])
for d in MISTE_MAX:
    pos = cal.searchsorted(pd.Timestamp(d)); fuori.iloc[max(0, pos - PRIMA):min(len(cal), pos + 180)] = True
ok = (~fuori).to_numpy(); anni = cal.year.to_numpy()
BL = {"1990-2004": (anni <= 2004), "2005-2020": (anni >= 2005) & (anni <= 2020)}
valido = (anni <= 2020)
res = {"base": {yn: round(float(np.nanmean(Y[yn].to_numpy()[ok & valido])), 4) for yn in Y.columns}, "stati": {}}
for sn, s in stati.items():
    sa = s.to_numpy().astype(bool)
    r = {"frazione": round(float(sa[ok & valido].mean()), 3), "episodi_1990_2020": RC.episodi_indip(pd.Series(sa & valido))}
    for yn in Y.columns:
        y = Y[yn].to_numpy(); rr = {}
        for bn, bm in BL.items():
            d, n, pa, pb = RC.dr(y, sa, ok & bm)
            rr[bn] = {"DR": None if np.isnan(d) else round(float(d), 4), "n": n, "P_dentro": None if pa is None or np.isnan(pa) else round(pa, 4), "P_fuori": None if pb is None or np.isnan(pb) else round(pb, 4),
                      "IC90": RC.ic_dr(y[bm], sa[bm], ok[bm], anni[bm]) if not np.isnan(d) else None}
        r[yn] = rr
        if sn != "K controllo":   # contro il controllo K
            for bn, bm in BL.items():
                m = ok & bm & (sa | stati["K controllo"].to_numpy().astype(bool))
                d, n, pa, pb = RC.dr(y, sa, m)
                r[yn][bn]["DR_vs_K"] = None if np.isnan(d) else round(float(d), 4)
    res["stati"][sn] = r
nul = []; n = len(cal)
for _ in range(500):
    k = int(rng.integers(504, n - 504)); mx = -9
    for sn in ("A", "B", "C"):
        sh = np.roll(stati[sn].to_numpy().astype(bool), k)
        for yn in Y.columns:
            d, *_ = RC.dr(Y[yn].to_numpy(), sh, ok & BL["2005-2020"])
            if not np.isnan(d): mx = max(mx, d)
    nul.append(mx)
res["soglia_migliore_fra_9"] = round(float(np.percentile(nul, 95)), 4)
# tempo tipico dall'accensione (inizio episodio) al superamento di 60; episodi 2021-2026
def inizi(s, gap=126):
    ix = np.flatnonzero(s.to_numpy()); out = []
    for i in ix:
        if not out or i - out[-1] >= gap: out.append(i)
    return out
desc = {}
for sn in ("A", "B", "C"):
    righe = []
    for i in inizi(stati[sn]):
        d0 = cal[i]; f = a.iloc[i + 1:i + 253]; salto = f[f >= 60]
        dd = (sp.reindex(cal).iloc[i + 1:i + 64].min() / sp.reindex(cal).iloc[i] - 1) if i + 64 < len(cal) else None
        righe.append({"data": str(d0.date()), "giorni_a_60": None if salto.empty else int((salto.index[0] - d0).days), "calo_63g": None if dd is None or np.isnan(dd) else round(float(dd), 3)})
    desc[sn] = righe
res["episodi"] = desc
res["oggi"] = {"M21": round(float(M21.iloc[-1]), 1), "M21_42g_fa": round(float(M21.iloc[-43]), 1), "M63": round(float(M63.iloc[-1]), 1), "M63_63g_fa": round(float(M63.iloc[-64]), 1), "A": bool(A.iloc[-1]), "B": bool(B.iloc[-1]), "C": bool(C.iloc[-1]), "K": bool(K.iloc[-1]), "armor": round(float(a.iloc[-1]), 1)}
json.dump(res, open("scratch/salita_lenta_esito.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in res.items() if k != "episodi"}, indent=0, ensure_ascii=False)[:7000])
