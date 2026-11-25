"""Segue PROTOCOLLO_MINIMI_3.md (commit 1519990, scritto prima dei calcoli)."""
import json, sys, warnings
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
warnings.filterwarnings("ignore")
sys.path.insert(0, "src")
from armor import store, occasione as oc
sp = store.load("sp500").dropna(); sp = sp[sp.index >= "1949-01-01"]; ix = sp.index
r = sp.pct_change()
mx252, mx63, mn63 = sp.rolling(252).max(), sp.rolling(63).max(), sp.rolling(63).min()
ma50, ma200 = sp.rolling(50).mean(), sp.rolling(200).mean()
vol21, vol63 = r.rolling(21).std(), r.rolling(63).std()
dm = (sp == mn63).astype(float); since = pd.Series(np.arange(len(sp)), index=ix).where(dm == 1).ffill(); dsl = (pd.Series(np.arange(len(sp)), index=ix) - since).clip(upper=63)
P = pd.DataFrame({"dd252": sp / mx252 - 1, "dd63": sp / mx63 - 1, "rimb": sp / mn63 - 1, "dal_min": dsl, "r5": sp.pct_change(5), "r21": sp.pct_change(21),
                  "r63": sp.pct_change(63), "m50": sp / ma50 - 1, "m200": sp / ma200 - 1, "pend50": ma50 / ma50.shift(21) - 1, "vol21": vol21, "vol_rap": vol21 / vol63,
                  "giorni_neri": (r < -0.01).astype(float).rolling(21).sum()})
al = lambda s: s.dropna().reindex(ix, method="ffill")
vix, v3, baa = al(store.load("vix")), al(store.load("vix3m")), al(store.load("baa10y"))
S = oc.serie_archivio()
sett = pd.DataFrame({k: al(v) for k, v in S["settori"].items() if len(v)})
V = pd.DataFrame({"vix_pct": vix.expanding(252).rank(pct=True), "vix_su_max": vix / vix.rolling(63).max(), "vix_term": (vix / v3).where(v3.notna()),
                  "baa_var": baa - baa.shift(21), "baa_su_max": baa / baa.rolling(63).max(),
                  "settori_50": (sett > sett.rolling(50).mean()).mean(axis=1).where(sett.notna().all(axis=1))})
V.loc[V.index < "1999-01-01"] = np.nan
V["vix_term"] = V["vix_term"].fillna(V["vix_term"].median()) if V["vix_term"].notna().any() else V["vix_term"]
V.loc[V["vix_pct"].isna(), "vix_term"] = np.nan
PV = pd.concat([P, V], axis=1)
mn21 = pd.concat([sp.shift(-i) for i in range(1, 22)], axis=1).min(axis=1) / sp - 1
f21 = sp.shift(-21) / sp - 1; ok = f21.notna()
F1 = (mn21 <= -0.05).astype(float).where(ok); F3 = ((f21 > 0) & (mn21 >= -0.02)).astype(float).where(ok)
stress = (P["dd252"] <= -0.08)
d = oc.calcola(S); G0 = pd.concat([d["panico_rec"], 100 - d["svolta"]], axis=1).min(axis=1, skipna=False).reindex(ix)

def modello(nome):
    if nome == "G1": return P, False, lambda: LogisticRegression(C=0.1, max_iter=500), 1500
    if nome == "G2": return PV, False, lambda: LogisticRegression(C=0.1, max_iter=500), 1500
    if nome == "G3": return P, True, lambda: LogisticRegression(C=0.1, max_iter=500), 300
    if nome == "G4": return PV, True, lambda: LogisticRegression(C=0.1, max_iter=500), 300
    if nome == "G5": return PV, False, lambda: GradientBoostingClassifier(max_depth=2, n_estimators=100, learning_rate=0.05, random_state=0), 1500
prob = {}
for nome in ("G1", "G2", "G3", "G4", "G5"):
    X, solo_stress, mk, minrow = modello(nome)
    out = pd.Series(np.nan, index=ix)
    for Y in range(1975, 2027):
        te = (ix.year == Y); tr_end = np.where(te)[0][0] - 63
        tr = pd.Series(False, index=ix); tr.iloc[:max(tr_end, 0)] = True
        m = tr & F1.notna() & X.notna().all(axis=1)
        if solo_stress: m &= stress
        if m.sum() < minrow: continue
        sc = StandardScaler().fit(X[m]); mod = mk().fit(sc.transform(X[m]), F1[m])
        xt = X[te & X.notna().all(axis=1)]
        if len(xt): out.loc[xt.index] = mod.predict_proba(sc.transform(xt))[:, 1]
    prob[nome] = out
    print(nome, "previsioni", int(out.notna().sum()), "dal", out.dropna().index[0].date(), flush=True)
C = pd.DataFrame({"G0 Minimi attuale": G0, **{k: v for k, v in prob.items()}})
Cp = C.copy()   # punteggi 1-100: percentile espanso della probabilita' nelle previsioni passate
for k in prob: Cp[k] = 1 + 99 * prob[k].expanding(252).rank(pct=True)

def auc(s, y):
    s = np.asarray(s, float); y = np.asarray(y, float); n1 = int(y.sum()); n0 = len(y) - n1
    if n1 < 3 or n0 < 3: return np.nan
    rk = pd.Series(s).rank().to_numpy(); return float((rk[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))
rng = np.random.default_rng(2513); out = {}
ver = ix >= "2013-01-01"
for per, pm in (("sotto stress", stress), ("tutti i giorni", pd.Series(True, index=ix))):
    base = pm & pd.Series(ver, index=ix) & F1.notna() & C.notna().all(axis=1)
    idx = np.where(base)[0]; years = ix[idx].year; ys = np.array(sorted(set(years)))
    gr = {a: idx[years == a] for a in ys}
    y1, y3 = F1.to_numpy(), F3.to_numpy(); fr = f21.to_numpy()
    res = {"giorni": int(len(idx)), "base_F1_%": float(np.nanmean(y1[idx]) * 100), "base_F3_%": float(np.nanmean(y3[idx]) * 100), "modelli": {}}
    A = {k: C[k].to_numpy() for k in C}
    for k in C:
        a1 = auc(A[k][idx], y1[idx]); a3 = auc(-A[k][idx], y3[idx])
        rho = float(pd.Series(A[k][idx]).corr(pd.Series(fr[idx]), method="spearman"))
        b1, b3 = [], []
        for _ in range(500):
            ii = np.concatenate([gr[a] for a in rng.choice(ys, len(ys))])
            b1.append(auc(A[k][ii], y1[ii])); b3.append(auc(-A[k][ii], y3[ii]))
        res["modelli"][k] = {"AUC_F1": a1, "IC90_F1": [float(np.nanpercentile(b1, 5)), float(np.nanpercentile(b1, 95))],
                             "AUC_F3": a3, "IC90_F3": [float(np.nanpercentile(b3, 5)), float(np.nanpercentile(b3, 95))], "spearman_R": rho}
    best1, best3 = [], []
    for _ in range(200):
        perm = dict(zip(ys, rng.permutation(ys))); f1s = y1[idx].copy(); f3s = y3[idx].copy()
        for a in ys:
            pos = np.where(years == a)[0]; src = np.where(years == perm[a])[0]
            f1s[pos] = np.resize(y1[idx][src], len(pos)); f3s[pos] = np.resize(y3[idx][src], len(pos))
        best1.append(np.nanmax([auc(A[k][idx], f1s) for k in C])); best3.append(np.nanmax([auc(-A[k][idx], f3s) for k in C]))
    res["soglia_caso_F1"] = float(np.percentile(best1, 95)); res["soglia_caso_F3"] = float(np.percentile(best3, 95))
    # rendimento medio a 21 sedute con punteggio alto/basso
    res["rend21"] = {}
    for k in C:
        sc = Cp[k].to_numpy() if k != "G0 Minimi attuale" else C[k].to_numpy(); h, l = idx[sc[idx] >= 80], idx[sc[idx] <= 20]
        res["rend21"][k] = {"alto>=80": [int(len(h)), float(np.nanmean(fr[h]) * 100) if len(h) else None], "basso<=20": [int(len(l)), float(np.nanmean(fr[l]) * 100) if len(l) else None]}
    out[per] = res
    print(f"\n=== {per}: giorni {res['giorni']} base F1 {res['base_F1_%']:.1f}% F3 {res['base_F3_%']:.1f}% | soglia caso F1 {res['soglia_caso_F1']:.3f} F3 {res['soglia_caso_F3']:.3f}")
    for k, v in res["modelli"].items():
        print(f"  {k:20s} F1 {v['AUC_F1']:.3f} [{v['IC90_F1'][0]:.3f},{v['IC90_F1'][1]:.3f}]  F3 {v['AUC_F3']:.3f} [{v['IC90_F3'][0]:.3f},{v['IC90_F3'][1]:.3f}]  rho {v['spearman_R']:+.3f}  21gg alto {res['rend21'][k]['alto>=80']} basso {res['rend21'][k]['basso<=20']}")
# secondaria: fuori campione prima del 2013 (solo modelli con previsioni)
sec = {}
pre = (ix < "2013-01-01") & stress.to_numpy() & F1.notna().to_numpy()
for k in ("G1", "G3", "G2", "G4", "G5"):
    m = pre & C[k].notna().to_numpy()
    sec[k] = {"giorni": int(m.sum()), "AUC_F1": auc(C[k].to_numpy()[m], F1.to_numpy()[m]), "AUC_F3": auc(-C[k].to_numpy()[m], F3.to_numpy()[m])}
out["secondaria_prima_2013_sotto_stress"] = sec; print("\nsecondaria (prima del 2013, sotto stress):", {k: (v['giorni'], round(v['AUC_F1'], 3), round(v['AUC_F3'], 3)) for k, v in sec.items()})
out["oggi"] = {k: float(Cp[k].dropna().iloc[-1]) if k != "G0 Minimi attuale" else float(C[k].dropna().iloc[-1]) for k in C}
print("oggi:", out["oggi"])
json.dump(out, open("scratch/minimi_3_esito.json", "w"), indent=1, default=float)
Cp.dropna(how="all").to_csv("/tmp/minimi3_punteggi.csv")
