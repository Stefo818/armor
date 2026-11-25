"""Indice crollo 2: segue PROTOCOLLO_INDICE_CROLLO_2.md (commit dcf7bd8, scritto prima dei calcoli)."""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "src"); sys.path.insert(0, "scratch")
from armor import indice_crollo as ic, predisposizione as pr, spia_caro, store  # noqa: E402
from classifica_40anni import ESTERNI, MISTE_MAX  # noqa: E402

X = ic.calcola_serie(); cal = X.index
spf = store.load("sp500").dropna(); spf = spf[~spf.index.duplicated()]
sp = spf.reindex(cal).ffill()

def pexp(s, minp=252):
    return s.expanding(min_periods=minp).rank(pct=True)
def daily(s, lag=0, minp=252):
    """Percentile espanso (solo passato) di una serie, ritardata di `lag` giorni di calendario, portata sul calendario di Borsa."""
    s = s.dropna(); s = s[~s.index.duplicated()]
    if lag:
        s = s.copy(); s.index = s.index + pd.Timedelta(days=lag)
    p = pexp(s, minp)
    return p.reindex(p.index.union(cal)).ffill().reindex(cal)
def L(k):
    return store.load(k).dropna()

# ---- V1..V4
PES = dict(ic.PESI)
def punteggio(pesi):
    w = pd.Series(pesi); w = w / w.sum()
    return sum(X[c].fillna(50.0) * w[c] for c in w.index)
S1 = punteggio(PES); S2 = punteggio({k: v for k, v in PES.items() if k != "f8_perdita"})
d07 = spia_caro.punteggio()
D07 = daily(d07.reindex(d07.index), 0, 252)
V1 = pexp(S1); V2 = pexp(S2)
V3 = 0.8 * V1 + 0.2 * D07.fillna(0.5); V4 = 0.8 * V2 + 0.2 * D07.fillna(0.5)
print("controllo: correlazione V1 con l'indice ufficiale", round(float(V1.corr(X["indice"], method="spearman")), 4))

# ---- N1..N6
vol63 = np.log(spf).diff().rolling(63).std()
N = {}
bl = L("busloans"); n1a = np.log(bl) - np.log(bl.shift(36))
N["N1 credito e prezzi insieme"] = daily(n1a, 45, 60) * daily(spf / spf.shift(756) - 1, 0)
baa = L("baa10y")
N["N2 credito che si rovina dal basso"] = (1 - daily(baa, 1)) * daily(baa - baa.shift(20), 1)
N["N3 calma e mercato caro"] = (1 - daily(vol63, 0)) * daily(L("cape_m"), 45, 60)
N["N4 salita eccessiva con volatilita"] = daily(spf / spf.shift(504) - 1, 0) * daily(vol63, 0)
comp = pr.componenti(X); Pm = comp.mean(axis=1, skipna=True).where(comp.notna().sum(axis=1) >= 5)
trig = (X["f2_salto"] + X["f3_curva"]) / 2
N["N5 terreno fragile x innesco"] = pexp(Pm) * pexp(trig)
nf = L("nfci")
liq = daily(-L("net_liq_13w"), 7, 60); nfc = daily(nf - nf.shift(13), 7, 60); r2 = daily(L("dgs2") - L("dgs2").shift(63), 1)
stack = pd.concat([liq, nfc, r2], axis=1)
N["N6 stretta di liquidita e tassi"] = stack.mean(axis=1, skipna=True).where(stack.notna().sum(axis=1) >= 2)

cand = {"V1 attuale": V1, "V2 senza distanza dal massimo": V2, "V3 attuale + CAPE": V3, "V4 senza distanza + CAPE": V4}
for k, v in N.items():
    cand[k + " (da solo)"] = v
for k, v in N.items():
    cand[k + " (misto 50/50)"] = 0.5 * V1 + 0.5 * v.fillna(0.5)
C = pd.DataFrame(cand).reindex(cal)

# ---- giorni e bersagli (come PROTOCOLLO_SFASATO)
fuori = pd.Series(False, index=cal)
for d in ESTERNI:
    p = cal.searchsorted(pd.Timestamp(d)); fuori.iloc[max(0, p - 63):min(len(cal), p + 61)] = True
for d in MISTE_MAX:
    p = cal.searchsorted(pd.Timestamp(d)); fuori.iloc[max(0, p - 5):min(len(cal), p + 181)] = True
dd = sp / sp.rolling(252, min_periods=120).max() - 1
ok = (~fuori) & (dd >= -0.05) & (sp.pct_change(5) > -0.02)
def mn(a, b):
    return pd.concat([sp.shift(-i) for i in range(a, b + 1)], axis=1).min(axis=1) / sp - 1
m15, m621, m2263, m121 = mn(1, 5), mn(6, 21), mn(22, 63), mn(1, 21)
Y = {"E1 giorni": (m15 <= -0.03).astype(float).where(m15.notna()),
     "E2 settimane": ((m621 <= -0.05) & (m15 > -0.03)).astype(float).where(m621.notna()),
     "E3 mesi": ((m2263 <= -0.08) & (m121 > -0.05)).astype(float).where(m2263.notna())}
sel = ok & (cal <= "2014-12-31"); ver = ok & (cal >= "2015-01-01")

def auc(s, y):
    s = np.asarray(s, float); y = np.asarray(y, float)
    n1 = int(y.sum()); n0 = len(y) - n1
    if n1 < 3 or n0 < 3:
        return np.nan
    r = pd.Series(s).rank().to_numpy()
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))
def episodi(y):
    pos = np.where(np.asarray(y) == 1)[0]
    return 0 if len(pos) == 0 else 1 + int((np.diff(pos) > 20).sum())

rng = np.random.default_rng(2511)
out = {"eventi": {}}
for ev, y in Y.items():
    ms = sel & y.notna(); mv = ver & y.notna()
    ys, yv = y[ms], y[mv]
    Cs, Cv = C[ms].fillna(0.5), C[mv].fillna(0.5)
    ep = (episodi(ys.to_numpy()), episodi(yv.to_numpy()))
    a_s = {k: auc(Cs[k], ys) for k in C}; a_v = {k: auc(Cv[k], yv) for k in C}
    # intervallo al 90% per blocchi d'anno (verifica)
    anni = np.array(sorted(set(Cv.index.year))); gr = {a: np.where(Cv.index.year == a)[0] for a in anni}
    ic90 = {}
    if ep[1] >= 6:
        boot = {k: [] for k in C}
        for _ in range(500):
            sc = rng.choice(anni, len(anni)); idx = np.concatenate([gr[a] for a in sc]); yy = yv.to_numpy()[idx]
            for k in C:
                boot[k].append(auc(Cv[k].to_numpy()[idx], yy))
        ic90 = {k: (float(np.nanpercentile(boot[k], 5)), float(np.nanpercentile(boot[k], 95))) for k in C}
    # soglia del caso: migliore dei 16 con bersagli di verifica mescolati per anno
    best = []
    if ep[1] >= 6:
        for _ in range(200):
            mp = dict(zip(anni, rng.permutation(anni))); fin = np.zeros(len(yv))
            for a in anni:
                src = yv.to_numpy()[gr[mp[a]]]; fin[gr[a]] = np.resize(src, len(gr[a]))
            best.append(np.nanmax([auc(Cv[k], fin) for k in C]))
    soglia = float(np.percentile(best, 95)) if best else None
    print(f"\n=== {ev}: episodi scelta {ep[0]} verifica {ep[1]} | giorni scelta {len(ys)} verifica {len(yv)} | eventi {int(ys.sum())}/{int(yv.sum())} | soglia del caso (migliore di {len(C.columns)}): {soglia if soglia is None else round(soglia, 3)}")
    for k in C:
        iv = ic90.get(k)
        print(f"  {k:46s} scelta {a_s[k]:.3f}  verifica {a_v[k]:.3f}" + (f"  IC90 [{iv[0]:.3f}, {iv[1]:.3f}]" if iv else ""))
    out["eventi"][ev] = {"episodi": ep, "soglia_caso": soglia, "scelta": a_s, "verifica": a_v, "ic90": ic90}

# ---- regole di accettazione
E1, E2 = out["eventi"]["E1 giorni"], out["eventi"]["E2 settimane"]
print("\n=== REGOLE (X sostituisce V1 solo se A1..A4)")
pas = []
for k in C:
    if k == "V1 attuale":
        continue
    a1 = (E1["scelta"][k] >= E1["scelta"]["V1 attuale"] + 0.03) and (E1["verifica"][k] >= E1["verifica"]["V1 attuale"] + 0.03)
    a2 = all(E2[p][k] >= E2[p]["V1 attuale"] - 0.02 for p in ("scelta", "verifica"))
    a3 = E1["soglia_caso"] is not None and E1["verifica"][k] > E1["soglia_caso"]
    a4 = bool(E1["ic90"]) and E1["ic90"][k][0] > 0.55
    print(f"  {k:46s} A1 {int(a1)} A2 {int(a2)} A3 {int(a3)} A4 {int(a4)}  (E1 scelta {E1['scelta'][k]:.3f} verifica {E1['verifica'][k]:.3f})")
    if a1 and a2 and a3 and a4:
        pas.append(k)
out["passano"] = pas
print("PASSANO:", pas if pas else "nessuno")
json.dump(out, open("scratch/indice_crollo_2_esito.json", "w"), indent=1, default=float)
