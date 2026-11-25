"""Segue PROTOCOLLO_MINIMI_4.md (commit d1168c5, scritto prima dei calcoli)."""
import json, sys, warnings
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
warnings.filterwarnings("ignore")
sys.path.insert(0, "src")
from armor import store
MERC = {"S&P 500": "sp500", "FTSE": "x_ftse", "CAC": "x_fchi", "SMI": "x_ssmi", "IBEX": "x_ibex", "AEX": "x_aex", "BEL20": "x_bfx", "HangSeng": "x_hsi",
        "Toronto": "x_gsptse", "Sydney": "x_axjo", "SanPaolo": "x_bvsp", "Seul": "x_ks11", "Taiwan": "x_twii", "Messico": "x_mxx"}
def feats(sp):
    ix = sp.index; r = sp.pct_change()
    mx252, mx63, mn63 = sp.rolling(252).max(), sp.rolling(63).max(), sp.rolling(63).min()
    ma50, ma200 = sp.rolling(50).mean(), sp.rolling(200).mean(); vol21, vol63 = r.rolling(21).std(), r.rolling(63).std()
    pos = pd.Series(np.arange(len(sp)), index=ix); since = pos.where(sp == mn63).ffill(); dsl = (pos - since).clip(upper=63)
    P = pd.DataFrame({"dd252": sp / mx252 - 1, "dd63": sp / mx63 - 1, "rimb": sp / mn63 - 1, "dal_min": dsl, "r5": sp.pct_change(5), "r21": sp.pct_change(21),
                      "r63": sp.pct_change(63), "m50": sp / ma50 - 1, "m200": sp / ma200 - 1, "pend50": ma50 / ma50.shift(21) - 1, "vol21": vol21, "vol_rap": vol21 / vol63,
                      "giorni_neri": (r < -0.01).astype(float).rolling(21).sum()})
    mn21 = pd.concat([sp.shift(-i) for i in range(1, 22)], axis=1).min(axis=1) / sp - 1; f21 = sp.shift(-21) / sp - 1
    P["F1"] = (mn21 <= -0.05).astype(float).where(f21.notna()); P["F3"] = ((f21 > 0) & (mn21 >= -0.02)).astype(float).where(f21.notna()); P["f21"] = f21
    P["stress"] = (P["dd252"] <= -0.08).astype(float); P["mercato"] = ""; return P
frames = []
for nome, k in MERC.items():
    try:
        s = store.load(k).dropna(); s = s[s.index >= "1989-01-01"]; s = s[~s.index.duplicated()]
        if len(s) < 2000: print(nome, "poca storia", len(s)); continue
        F = feats(s); F["mercato"] = nome; F = F.dropna(subset=["dd252", "vol_rap", "m200", "pend50"]); frames.append(F); print(nome, len(F), F.index[0].date())
    except Exception as e: print(nome, "NO", str(e)[:40])
D = pd.concat(frames).replace([np.inf, -np.inf], np.nan); D["anno"] = D.index.year; D = D.reset_index().rename(columns={D.index.name or "index": "data"})
X = ["dd252", "dd63", "rimb", "dal_min", "r5", "r21", "r63", "m50", "m200", "pend50", "vol21", "vol_rap", "giorni_neri"]
D = D.dropna(subset=X).reset_index(drop=True)
cfg = {"H1": (False, lambda: LogisticRegression(C=0.1, max_iter=500)), "H3": (True, lambda: LogisticRegression(C=0.1, max_iter=500)),
       "H5": (False, lambda: GradientBoostingClassifier(max_depth=2, n_estimators=100, learning_rate=0.05, random_state=0))}
for h in cfg: D[h] = np.nan
for Y in range(2000, 2027):
    tr_lim = pd.Timestamp(f"{Y}-01-01") - pd.Timedelta(days=95)
    tr = D[(D["data"] < tr_lim) & D["F1"].notna()]; te = D["anno"] == Y
    for h, (solo, mk) in cfg.items():
        t = tr[tr["stress"] == 1] if solo else tr
        if len(t) < 300 or te.sum() == 0: continue
        sc = StandardScaler().fit(t[X]); m = mk().fit(sc.transform(t[X]), t["F1"])
        D.loc[te, h] = m.predict_proba(sc.transform(D.loc[te, X]))[:, 1]
    print(Y, end=" ", flush=True)
print()
for h in cfg: D[h + "_pct"] = D.groupby("mercato")[h].transform(lambda s: 1 + 99 * s.expanding(252).rank(pct=True))
def auc(s, y):
    s = np.asarray(s, float); y = np.asarray(y, float); n1 = int(y.sum()); n0 = len(y) - n1
    if n1 < 3 or n0 < 3: return np.nan
    rk = pd.Series(s).rank().to_numpy(); return float((rk[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))
rng = np.random.default_rng(2514)
S = D[(D["stress"] == 1) & D["F1"].notna() & D[list(cfg)].notna().all(axis=1)].reset_index(drop=True)
anni = np.array(sorted(S["anno"].unique())); gr = {a: np.where(S["anno"] == a)[0] for a in anni}
print("giorni sotto stress OOS:", len(S), "base F1 %.1f%% F3 %.1f%%" % (S["F1"].mean() * 100, S["F3"].mean() * 100), "mercati", S["mercato"].nunique())
res = {"giorni": len(S), "modelli": {}}
for h in cfg:
    a1, a3 = auc(S[h], S["F1"]), auc(-S[h], S["F3"]); b1, b3 = [], []
    for _ in range(500):
        ii = np.concatenate([gr[a] for a in rng.choice(anni, len(anni))]); b1.append(auc(S[h].to_numpy()[ii], S["F1"].to_numpy()[ii])); b3.append(auc(-S[h].to_numpy()[ii], S["F3"].to_numpy()[ii]))
    hi, lo = S[S[h + "_pct"] >= 80], S[S[h + "_pct"] <= 20]
    per = {m: auc(g[h], g["F1"]) for m, g in S.groupby("mercato")}
    res["modelli"][h] = {"AUC_F1": a1, "IC90_F1": [float(np.nanpercentile(b1, 5)), float(np.nanpercentile(b1, 95))], "AUC_F3": a3, "IC90_F3": [float(np.nanpercentile(b3, 5)), float(np.nanpercentile(b3, 95))],
                         "rend21_alto": [len(hi), float(hi["f21"].mean() * 100)], "rend21_basso": [len(lo), float(lo["f21"].mean() * 100)],
                         "mercati_sopra_0.5": int(sum(v > 0.5 for v in per.values() if v == v)), "mercati_tot": int(sum(v == v for v in per.values())), "per_mercato": per}
best = []
for _ in range(200):
    S2 = S[["mercato", "anno", "F1"]].copy(); y = S["F1"].to_numpy().copy()
    for m, g in S.groupby("mercato"):
        ya = sorted(g["anno"].unique()); perm = dict(zip(ya, rng.permutation(ya)))
        for a in ya:
            pos = g.index[g["anno"] == a].to_numpy(); src = g.index[g["anno"] == perm[a]].to_numpy(); y[pos] = np.resize(S["F1"].to_numpy()[src], len(pos))
    best.append(max(auc(S[h], y) for h in cfg))
res["soglia_caso_F1"] = float(np.percentile(best, 95))
print("soglia del caso F1: %.3f" % res["soglia_caso_F1"])
for h, v in res["modelli"].items():
    print(f"{h}: F1 {v['AUC_F1']:.3f} [{v['IC90_F1'][0]:.3f},{v['IC90_F1'][1]:.3f}] F3 {v['AUC_F3']:.3f} [{v['IC90_F3'][0]:.3f},{v['IC90_F3'][1]:.3f}] | 21gg alto {v['rend21_alto'][0]} gg {v['rend21_alto'][1]:+.2f}%  basso {v['rend21_basso'][0]} gg {v['rend21_basso'][1]:+.2f}% | mercati>0.5: {v['mercati_sopra_0.5']}/{v['mercati_tot']}")
json.dump(res, open("scratch/minimi_4_esito.json", "w"), indent=1, default=float)
