"""Segue PROTOCOLLO_SUPER_ARMOR_ECONOMIA.md (scritto prima dei calcoli). Deviazione dichiarata: i confronti partono dal 1992 (storia minima di 5 anni delle serie finanziarie)."""
import json, sys, warnings
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler
warnings.filterwarnings("ignore")
sys.path.insert(0, "src")
from armor import store
L = lambda k: store.load(k).dropna()
ME = pd.date_range("1960-01-31", "2026-11-30", freq="ME")
def asof(s, lag):
    s = s.copy(); s.index = s.index + pd.Timedelta(days=lag)
    s = s[~s.index.duplicated(keep="last")]
    return s.reindex(s.index.union(ME)).ffill().reindex(ME).where(ME >= s.index[0])
pe = lambda s, m=60: s.expanding(m).rank(pct=True) * 100
# --- componenti (alto = peggio)
t3, t2, baa, nf, sp, vx = L("t10y3m"), L("t10y2y"), L("baa10y"), L("nfci"), L("sp500"), L("vix")
ic = L("icsa"); ic4 = ic.rolling(4).mean(); e1 = ic4 / ic4.rolling(52).min() - 1
pay, ind, cf, per, sa, um, un = L("payems"), L("indpro"), L("cfnai"), L("permit"), L("sahm"), L("umcsent"), L("unrate")
C = pd.DataFrame(index=ME)
C["F1"] = pe(-asof(t3, 1)); C["F2"] = pe(asof(baa, 1)); bm = asof(baa, 1); C["F3"] = pe(bm - bm.shift(6)); C["F4"] = pe(asof(nf, 7))
spm = asof(sp, 1); C["F5"] = pe(-(spm / spm.shift(12) - 1)); C["F6"] = pe(-asof(t2, 1)); C["F7"] = pe(asof(vx, 1))
C["E1"] = pe(asof(e1, 5)); C["E2"] = pe(-asof(pay.pct_change(3), 37)); C["E3"] = pe(-asof(ind.pct_change(3), 45)); C["E4"] = pe(-asof(cf, 45))
C["E5"] = pe(-asof(per.pct_change(6), 45)); C["E6"] = pe(asof(sa, 40)); C["E7"] = pe(-asof(um.pct_change(6), 20))
FIN, ECO = ["F1", "F2", "F3", "F4", "F5", "F6"], ["E1", "E2", "E3", "E4", "E5", "E6", "E7"]
# --- bersagli (mese di osservazione -> fine mese)
pi = lambda s: pd.Series(s.values, index=s.index.to_period("M"))
mo = lambda s: pi(s).groupby(level=0).last()
u, p, i_ = mo(un), mo(pay), mo(ind)
z = lambda x: x / x.std()
Z6 = (z(-(u.shift(-6) - u)) + z(np.log(p.shift(-6) / p)) + z(np.log(i_.shift(-6) / i_))) / 3
B = (-Z6); B.index = B.index.to_timestamp("M").normalize(); B = B.reindex(ME)
rec = mo(L("usrec")); rec.index = rec.index.to_timestamp("M").normalize(); rec = rec.reindex(ME).ffill()
R6 = pd.Series(np.nan, index=ME)
for k, t in enumerate(ME[:-6]):
    if rec.iloc[k] == 0: R6.iloc[k] = float(rec.iloc[k + 1:k + 7].max() == 1)
# ---- Segue PROTOCOLLO_SUPER_ARMOR_COSTI.md
cpi, wti, ff, d2 = L("cpi"), L("wti"), L("fedfunds"), L("dgs2")
cy = cpi.pct_change(12) * 100
C["K1"] = pe(asof(cy, 45)); C["K2"] = pe(asof(cy - cy.shift(6), 45))
w_ = asof(wti, 1); C["K3"] = pe(w_ / w_.shift(12) - 1)
f_ = asof(ff, 1); C["K4"] = pe(f_ - f_.shift(12)); g_ = asof(d2, 1); C["K5"] = pe(g_ - g_.shift(12))
mean = lambda cols: C[cols].mean(axis=1, skipna=True).where(C[cols].notna().sum(axis=1) >= max(1, len(cols) // 2))
KS = ["K1", "K2", "K3", "K4", "K5"]
fin, eco, cos = mean(FIN), mean(ECO), mean(KS)
mx = lambda *a: pd.concat(a, axis=1).max(axis=1, skipna=False)
S = pd.DataFrame(index=ME)
S["V0"] = mx(fin, eco); S["V1"] = mx(fin, eco, cos); S["V2"] = mx(mean(FIN + KS), eco); S["V3"] = mx(fin, mean(ECO + KS))
S["V4"] = mx(fin, eco, mean(["K1", "K2"])); S["V5"] = mx(fin, eco, C["K3"]); S["V6"] = mx(fin, eco, mean(["K4", "K5"]))
S["V7"] = pd.concat([fin, eco, cos], axis=1).mean(axis=1, skipna=False); S["V8"] = 0.5 * S["V0"] + 0.5 * cos
def sp_(a, b):
    d = pd.concat([a, b], axis=1).dropna(); return d.iloc[:, 0].corr(d.iloc[:, 1], method="spearman") if len(d) > 20 else np.nan
def auc(s, y):
    d = pd.concat([s, y], axis=1).dropna(); d.columns = ["s", "y"]; n1 = int(d.y.sum()); n0 = len(d) - n1
    if n1 < 3 or n0 < 3: return np.nan
    r = d.s.rank(); return float((r[d.y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))
ok = S.notna().all(axis=1) & B.notna() & (ME >= "2006-08-01")
print("mesi comuni", int(ok.sum()), ME[ok][0].date(), ME[ok][-1].date())
rng = np.random.default_rng(2525); res = {}
NUOVE = [f"V{i}" for i in range(1, 9)]
for lab, per in (("scelta 2006-2014", ok & (ME <= "2014-12-31")), ("verifica 2015-2026", ok & (ME >= "2015-01-01"))):
    idx = np.where(per)[0]; yrs = ME[idx].year; ys = np.array(sorted(set(yrs))); gr = {a: idx[yrs == a] for a in ys}
    r = {"mesi": int(len(idx)), "R6_positivi": int(R6.iloc[idx].sum(skipna=True)), "v": {}}
    base = sp_(S["V0"].iloc[idx], B.iloc[idx]); r["base"] = base; r["base_auc"] = auc(S["V0"].iloc[idx], R6.iloc[idx])
    for k in S:
        a = sp_(S[k].iloc[idx], B.iloc[idx]); dd = []
        for _ in range(300):
            ii = np.concatenate([gr[x] for x in rng.choice(ys, len(ys))]); dd.append(sp_(S[k].iloc[ii], B.iloc[ii]) - sp_(S["V0"].iloc[ii], B.iloc[ii]))
        r["v"][k] = {"rho": a, "delta": a - base, "IC90_delta": [float(np.nanpercentile(dd, 5)), float(np.nanpercentile(dd, 95))], "auc": auc(S[k].iloc[idx], R6.iloc[idx])}
    if lab.startswith("verifica"):
        best = []
        for _ in range(200):
            sh = int(rng.integers(24, 120)); Bs = pd.Series(np.roll(B.to_numpy(), sh), index=ME); b0 = sp_(S["V0"].iloc[idx], Bs.iloc[idx])
            best.append(np.nanmax([sp_(S[k].iloc[idx], Bs.iloc[idx]) - b0 for k in NUOVE]))
        r["soglia_caso_delta"] = float(np.percentile(best, 95))
    res[lab] = r
    print(f"\n=== {lab}: mesi {r['mesi']} (inizi recessione {r['R6_positivi']}) base V0 rho {base:+.3f}", ("soglia caso delta %.3f" % r["soglia_caso_delta"]) if "soglia_caso_delta" in r else "")
    for k, v in r["v"].items(): print(f"  {k}: rho {v['rho']:+.3f}  delta {v['delta']:+.3f} [{v['IC90_delta'][0]:+.3f},{v['IC90_delta'][1]:+.3f}]  AUC_R6 {v['auc']:.3f}")
# singole misure: segno e valore da sole
print("\nSingole misure (Spearman con Z6, alto=peggio atteso positivo):")
res["singole"] = {}
for k in KS + ["F1", "E1"]:
    row = {}
    for lab, per in (("tutto", ME >= "1992-01-01"), ("2006-2014", (ME >= "2006-08-01") & (ME <= "2014-12-31")), ("2015-2026", ME >= "2015-01-01")):
        row[lab] = sp_(C[k][per], B[per])
    res["singole"][k] = row; print(" ", k, {a: (None if pd.isna(b) else round(b, 2)) for a, b in row.items()})
res["oggi"] = {k: (None if pd.isna(C[k].iloc[-1]) else float(C[k].iloc[-1])) for k in KS}; res["oggi_V"] = {k: float(S[k].dropna().iloc[-1]) for k in S}
print("\nOggi (percentili):", {k: round(v, 1) for k, v in res["oggi"].items() if v is not None}, "V:", {k: round(v, 1) for k, v in res["oggi_V"].items()})
json.dump(res, open("scratch/super_armor_costi_esito.json", "w"), indent=1, default=float)
