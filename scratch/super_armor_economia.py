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
# --- riferimenti attuali
T = pd.read_csv("data/titan_storia.csv", index_col=0, parse_dates=True)
SAI = T["super_armor_index"].dropna().resample("ME").last().reindex(ME); ARM = T["armor_tarato"].dropna().resample("ME").last().reindex(ME)
mean = lambda cols: C[cols].mean(axis=1, skipna=True).where(C[cols].notna().sum(axis=1) >= max(2, len(cols) // 2))
fin, eco = mean(FIN), mean(ECO)
S = pd.DataFrame(index=ME)
for n, c in (("C1", "F1"), ("C2", "F2"), ("C3", "F4"), ("C4", "F5"), ("C5", "E1"), ("C6", "E4"), ("C7", "E2"), ("C8", "E5"), ("C9", "E6")): S[n] = C[c]
S["C10"] = fin; S["C11"] = eco; S["C12"] = 0.5 * fin + 0.5 * eco; S["C13"] = 0.7 * fin + 0.3 * eco; S["C14"] = 0.3 * fin + 0.7 * eco
S["C15"] = C.mean(axis=1, skipna=True).where(C.notna().sum(axis=1) >= 7); S["C16"] = pd.concat([fin, eco], axis=1).max(axis=1, skipna=False); S["C17"] = fin * eco / 100
S["C19"] = C[["F1", "F2", "E1", "E2"]].mean(axis=1, skipna=False); w = pd.Series({**{c: 3 for c in FIN}, **{c: 1 for c in ECO}})
S["C20"] = (C[FIN + ECO] * w).sum(axis=1, skipna=True) / (C[FIN + ECO].notna() * w).sum(axis=1)
S["C21"] = C[["F1", "F3", "F4", "F5", "E1", "E5", "E7"]].mean(axis=1, skipna=False); S["C22"] = fin * (50 + eco / 2) / 100
# addestrate a scorrimento annuale
X = C.fillna(50.0); S["C23"] = np.nan; S["C24"] = np.nan; S["C25"] = np.nan
for Y in range(1992, 2027):
    te = ME.year == Y; lim = ME[te][0] - pd.DateOffset(months=7); tr = (ME <= lim) & (ME >= "1976-01-01")
    m1 = tr & R6.notna().to_numpy(); m2 = tr & B.notna().to_numpy()
    if m1.sum() > 60 and R6[m1].sum() > 3:
        sc = StandardScaler().fit(X[m1]); S.loc[te, "C23"] = LogisticRegression(C=0.1, max_iter=500).fit(sc.transform(X[m1]), R6[m1]).predict_proba(sc.transform(X[te]))[:, 1]
    if m2.sum() > 60:
        sc = StandardScaler().fit(X[m2]); S.loc[te, "C24"] = Ridge(alpha=10).fit(sc.transform(X[m2]), B[m2]).predict(sc.transform(X[te]))
    if tr.sum() > 60:
        from sklearn.decomposition import PCA
        sc = StandardScaler().fit(X[tr]); pc = PCA(1).fit(sc.transform(X[tr])); v = pc.transform(sc.transform(X[tr]))[:, 0]
        sg = np.sign(np.corrcoef(v, S["C15"][tr].fillna(50))[0, 1]) or 1; S.loc[te, "C25"] = sg * pc.transform(sc.transform(X[te]))[:, 0]
# C18: tre migliori singole in scelta (1992-2004)
def sp_(a, b):
    d = pd.concat([a, b], axis=1).dropna(); return d.iloc[:, 0].corr(d.iloc[:, 1], method="spearman") if len(d) > 20 else np.nan
SC = (ME >= "1992-01-01") & (ME <= "2004-12-31")
sing = {c: sp_(C[c][SC], B[SC]) for c in FIN + ECO if C[c][SC].notna().sum() > 60}; top3 = sorted(sing, key=lambda k: -sing[k])[:3]
S["C18"] = C[top3].mean(axis=1, skipna=False); print("C18 usa:", top3, {k: round(sing[k], 2) for k in top3})
S["C26 SuperArmor"] = SAI; S["Rif Armor"] = ARM
S = S[[f"C{i}" for i in range(1, 26)] + ["C26 SuperArmor", "Rif Armor"]]
def auc(s, y):
    d = pd.concat([s, y], axis=1).dropna(); d.columns = ["s", "y"]; n1 = int(d.y.sum()); n0 = len(d) - n1
    if n1 < 3 or n0 < 3: return np.nan
    r = d.s.rank(); return float((r[d.y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))
ok = S.notna().all(axis=1) & B.notna() & (ME >= "1992-01-01"); print("mesi in comune", int(ok.sum()), "dal", ME[ok][0].date(), "al", ME[ok][-1].date())
rng = np.random.default_rng(2516); res = {}
for lab, per in (("scelta 1992-2004", ok & (ME <= "2004-12-31")), ("verifica 2005-2026", ok & (ME >= "2005-01-01"))):
    idx = np.where(per)[0]; yrs = ME[idx].year; ys = np.array(sorted(set(yrs))); gr = {a: idx[yrs == a] for a in ys}
    r = {"mesi": int(len(idx)), "R6_positivi": int(R6.iloc[idx].sum(skipna=True)), "punteggi": {}}
    for k in S:
        a = sp_(S[k].iloc[idx], B.iloc[idx]); bb = []
        for _ in range(300):
            ii = np.concatenate([gr[x] for x in rng.choice(ys, len(ys))]); bb.append(sp_(S[k].iloc[ii], B.iloc[ii]))
        r["punteggi"][k] = {"spearman": a, "IC90": [float(np.nanpercentile(bb, 5)), float(np.nanpercentile(bb, 95))], "AUC_R6": auc(S[k].iloc[idx], R6.iloc[idx]),
                            "sp_anticipo3": sp_(S[k].iloc[idx], B.shift(-3).iloc[idx]), "sp_anticipo9": sp_(S[k].iloc[idx], B.shift(-9).iloc[idx])}
    best = []
    for _ in range(200):
        sh = int(rng.integers(24, 120)); Bs = pd.Series(np.roll(B.to_numpy(), sh), index=ME)
        best.append(np.nanmax([sp_(S[k].iloc[idx], Bs.iloc[idx]) for k in S if not k.startswith(("C26", "Rif"))]))
    r["soglia_caso_spearman"] = float(np.percentile(best, 95)); res[lab] = r
    print(f"\n=== {lab}: mesi {r['mesi']} (inizi di recessione {r['R6_positivi']}) soglia caso {r['soglia_caso_spearman']:.3f}")
    for k, v in sorted(r["punteggi"].items(), key=lambda kv: -kv[1]["spearman"]):
        print(f"  {k:15s} rho {v['spearman']:+.3f} [{v['IC90'][0]:+.2f},{v['IC90'][1]:+.2f}]  AUC_R6 {v['AUC_R6']:.3f}  anticipo +3m {v['sp_anticipo3']:+.2f} +9m {v['sp_anticipo9']:+.2f}")
res["oggi"] = {k: (None if pd.isna(S[k].iloc[-1]) else float(S[k].iloc[-1])) for k in S}
res["componenti_oggi"] = {k: float(C[k].dropna().iloc[-1]) for k in C}; res["C18"] = top3
json.dump(res, open("scratch/super_armor_economia_esito.json", "w"), indent=1, default=float)
S.to_csv("/tmp/sae_punteggi.csv"); C.to_csv("/tmp/sae_comp.csv")
# criterio (d): AUC su R6 con intervallo al 90% (bootstrap per anno), verifica 2005-2026, per le formule principali
per = ok & (ME >= "2005-01-01"); idx = np.where(per)[0]; yrs = ME[idx].year; ys = np.array(sorted(set(yrs))); gr = {a: idx[yrs == a] for a in ys}
res["AUC_IC90_verifica"] = {}
for k in ("C16", "C12", "C14", "C15", "C17", "C26 SuperArmor", "Rif Armor", "C7"):
    bb = []
    for _ in range(500):
        ii = np.concatenate([gr[x] for x in rng.choice(ys, len(ys))]); bb.append(auc(S[k].iloc[ii], R6.iloc[ii]))
    res["AUC_IC90_verifica"][k] = {"AUC": auc(S[k].iloc[idx], R6.iloc[idx]), "IC90": [float(np.nanpercentile(bb, 5)), float(np.nanpercentile(bb, 95))]}
    print(k, "AUC_R6", round(res["AUC_IC90_verifica"][k]["AUC"], 3), [round(x, 3) for x in res["AUC_IC90_verifica"][k]["IC90"]])
# episodi: valore medio del punteggio 6 mesi prima dell'inizio di ogni recessione
ons = [t for t in ME[1:] if rec.loc[t] == 1 and rec.shift(1).loc[t] == 0 and t >= pd.Timestamp("1992-01-01")]
res["prima_recessioni"] = {}
for t in ons:
    t6 = t - pd.DateOffset(months=6); t6 = ME[ME.get_indexer([t6], method="nearest")[0]]
    res["prima_recessioni"][str(t.date())] = {k: (None if pd.isna(S[k].loc[t6]) else round(float(S[k].loc[t6]), 1)) for k in ("C16", "C12", "C26 SuperArmor", "Rif Armor")}
print("6 mesi prima delle recessioni:", res["prima_recessioni"])
json.dump(res, open("scratch/super_armor_economia_esito.json", "w"), indent=1, default=float)
