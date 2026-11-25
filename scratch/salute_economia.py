"""Segue PROTOCOLLO_SALUTE_ECONOMIA.md (scritto prima dei calcoli)."""
import json, sys, warnings
import numpy as np, pandas as pd
from scipy.optimize import nnls
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.decomposition import PCA
warnings.filterwarnings("ignore")
sys.path.insert(0, "src")
from armor import store
L = lambda k: store.load(k).dropna()
def FR(i):
    d = pd.read_csv(f"/tmp/fred/{i}.csv", index_col=0, parse_dates=True); return pd.to_numeric(d.iloc[:, 0], errors="coerce").dropna()
ME = pd.date_range("1989-01-31", "2026-11-30", freq="ME")
def asof(s, lag):
    s = s.copy(); s.index = s.index + pd.Timedelta(days=lag); s = s[~s.index.duplicated(keep="last")]
    return s.reindex(s.index.union(ME)).ffill().reindex(ME).where(ME >= s.index[0])
X = pd.DataFrame(index=ME)
ic = L("icsa"); ic4 = ic.rolling(4).mean(); X["L1"] = asof(ic4 / ic4.rolling(52).min() - 1, 5)
X["L2"] = -asof(L("payems").pct_change(3), 37); X["L3"] = -asof(L("indpro").pct_change(3), 45); X["L4"] = -asof(L("cfnai"), 45)
X["L5"] = -asof(L("permit").pct_change(6), 45); X["L6"] = asof(L("sahm"), 40); X["L7"] = -asof(L("umcsent").pct_change(6), 20)
X["G1"] = -asof(FR("GDPC1").pct_change(4) * 100, 120); X["G2"] = -asof(FR("CLVMNACSCAB1GQEA19").pct_change(4) * 100, 120)
cy = L("cpi").pct_change(12) * 100; X["K1"] = asof(cy, 45); X["K2"] = asof(cy - cy.shift(6), 45)
w = asof(L("wti"), 1); X["K3"] = w / w.shift(12) - 1
f_ = asof(L("fedfunds"), 1); X["K4"] = f_ - f_.shift(12); g_ = asof(L("dgs2"), 1); X["K5"] = g_ - g_.shift(12)
mg = asof(FR("MORTGAGE30US"), 3); X["M1"] = mg - mg.shift(12); X["M2"] = mg
X["M3"] = asof(FR("DRSFRMACBS"), 75); X["M4"] = asof(FR("DRCCLACBS"), 75); X["M5"] = asof(FR("DRTSCLCC"), 45)
X["M6"] = -asof(FR("TOTALSL").pct_change(12), 45); X["M7"] = asof(FR("TDSP"), 90)
X = X.loc["1990-01-31":]; idx = X.index; n = len(idx)
PL = {"L": [f"L{i}" for i in range(1, 8)], "G": ["G1", "G2"], "K": [f"K{i}" for i in range(1, 6)], "M": [f"M{i}" for i in range(1, 8)]}
ALL = PL["L"] + PL["G"] + PL["K"] + PL["M"]
# ---- bersaglio T
rec = FR("USREC").reindex(idx, method="ffill") if False else None
us = FR("USREC"); us.index = us.index + pd.offsets.MonthEnd(0); us = us.groupby(level=0).last().reindex(idx).fillna(0)
T = pd.Series(0.0, index=idx); lvl = pd.Series(0.0, index=idx)
forti = [("2007-12-31", "2009-06-30"), ("2020-02-29", "2020-04-30")]; lievi = [("1990-07-31", "1991-03-31"), ("2001-03-31", "2001-11-30")]
for lv, per in ((100, forti), (60, lievi)):
    for a, b in per:
        m = (idx >= a) & (idx <= b); T[m] = lv
        k = np.where(idx > b)[0][:12]
        for j, i in enumerate(k, 1): T.iloc[i] = max(T.iloc[i], lv * (1 - j / 12))
vera_esp = (T == 0).to_numpy()
REC = us.to_numpy()
# ---- blocchi (lascia fuori una recessione)
cuts = [pd.Timestamp("1996-03-31"), pd.Timestamp("2004-12-31"), pd.Timestamp("2014-06-30")]
fold = np.digitize(idx.values.astype("datetime64[ns]").astype(np.int64), [c.value for c in cuts])
# ---- pre-calcolo dei riferimenti (indici di oggi nell'app)
from armor import super_armor_2 as s2
S2 = s2.calcola(); R0 = S2["sea"].resample("ME").last().reindex(idx); R1 = (S2["sa_eco"].resample("ME").last().reindex(idx))
def ols(s, t):
    ok = ~np.isnan(s) & ~np.isnan(t); s_, t_ = s[ok], t[ok]
    if s_.std() == 0: return t_.mean(), 0.0
    b = np.cov(s_, t_)[0, 1] / s_.var(ddof=1); b = max(b, 0.0); return t_.mean() - b * s_.mean(), b
def prep(tr):   # standardizza sul training; mancanti = 0
    mu, sd = X.iloc[tr].mean(), X.iloc[tr].std().replace(0, np.nan)
    Z = ((X - mu) / sd).fillna(0.0); return Z
def pil(Z, k): return Z[PL[k]].mean(axis=1)
def modello(nome, Z, tr, te, Tt, flag):
    """restituisce (score_train, score_test)"""
    cols = {"E1": PL["L"], "E2": PL["L"] + PL["G"], "E3": PL["L"] + PL["G"] + PL["M"], "E4": PL["L"] + PL["G"] + PL["K"], "E5": ALL, "E6": PL["G"]}
    if nome in cols:
        s = Z[cols[nome]].mean(axis=1); return s.iloc[tr].to_numpy(), s.iloc[te].to_numpy()
    P = pd.DataFrame({k: pil(Z, k) for k in PL})
    if nome == "E7": s = P.mean(axis=1)
    elif nome == "E8": s = P[["L", "G"]].mean(axis=1)
    elif nome == "X5": s = P.max(axis=1)
    elif nome == "X6": s = P[["L", "G"]].max(axis=1)
    elif nome == "X7": s = Z[ALL].median(axis=1)
    elif nome == "X8": s = Z[PL["L"] + PL["G"]].apply(lambda r: np.sort(r.to_numpy())[-5:].mean(), axis=1)
    elif nome in ("W1", "W2", "W3", "W4", "W5", "W8"):
        c = {"W1": ALL, "W2": PL["L"] + PL["G"], "W3": PL["L"] + PL["G"] + PL["M"], "W4": ALL, "W5": PL["L"] + PL["G"], "W8": PL["L"] + PL["G"] + PL["K"]}[nome]
        A, y = Z[c].iloc[tr].to_numpy(), Tt[tr] - np.nanmean(Tt[tr])
        if nome in ("W4", "W5"):
            m = Ridge(alpha=10, fit_intercept=False).fit(A, y); wv = np.clip(m.coef_, 0, None)
        else: wv, _ = nnls(A, y)
        s = pd.Series(Z[c].to_numpy() @ wv, index=Z.index)
    elif nome in ("W6", "W7"):
        c = ["L", "G", "K", "M"] if nome == "W6" else ["L", "G", "M"]
        A, y = P[c].iloc[tr].to_numpy(), Tt[tr] - np.nanmean(Tt[tr]); wv, _ = nnls(A, y); s = pd.Series(P[c].to_numpy() @ wv, index=Z.index)
    elif nome in ("X1", "X2"):
        c = ALL if nome == "X1" else PL["L"] + PL["G"]
        m = LogisticRegression(C=0.1, max_iter=500).fit(Z[c].iloc[tr], flag[tr]); s = pd.Series(m.predict_proba(Z[c])[:, 1], index=Z.index)
    elif nome in ("X3", "X4"):
        c = ALL if nome == "X3" else PL["L"] + PL["G"]
        p = PCA(1).fit(Z[c].iloc[tr]); v = p.transform(Z[c])[:, 0]; sg = np.sign(np.corrcoef(v[tr], Tt[tr])[0, 1]) or 1; s = pd.Series(sg * v, index=Z.index)
    return s.iloc[tr].to_numpy(), s.iloc[te].to_numpy()
NOMI = ["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8", "X1", "X2", "X3", "X4", "X5", "X6", "X7", "X8"]
def oof(Tt, flag):
    out = {k: np.full(n, np.nan) for k in NOMI}
    for f in range(4):
        te = np.where(fold == f)[0]; tr = np.where(fold != f)[0]; Z = prep(tr)
        for k in NOMI:
            st, se = modello(k, Z, tr, te, Tt, flag); a, b = ols(st, Tt[tr]); out[k][te] = np.clip(a + b * se, 0, 100)
    return out
def rmse(p, Tt): ok = ~np.isnan(p); return float(np.sqrt(np.mean((p[ok] - Tt[ok]) ** 2)))
def auc(p, y):
    from scipy.stats import rankdata
    n1 = int(y.sum()); n0 = len(y) - n1; r = rankdata(p); return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))
Tt = T.to_numpy(); flag = REC.copy()
O = oof(Tt, flag)
deep = (Tt == 100)
tab = {}
for k in NOMI + ["R0", "R1"]:
    p = O[k] if k in O else (R0 if k == "R0" else R1).to_numpy()
    ok = ~np.isnan(p)
    tab[k] = {"rmse": rmse(p, Tt), "auc": auc(p[ok], REC[ok]), "medio_forti": float(np.nanmean(p[deep])), "falsi_allarmi": float((p[vera_esp & ok] >= 60).mean())}
print(f"{n} mesi, forti {int(deep.sum())}, lievi {int((T == 60).sum())}, vera espansione {int(vera_esp.sum())}")
print("alternativa  RMSE   AUC  medio_forti  falsi_allarmi")
for k, v in sorted(tab.items(), key=lambda kv: kv[1]["rmse"]): print(f"  {k:3s}  {v['rmse']:6.2f}  {v['auc']:.3f}  {v['medio_forti']:6.1f}  {v['falsi_allarmi']*100:5.1f}%")
# soglia migliore fra N
rng = np.random.default_rng(2526); best = []
for _ in range(100):
    sh = int(rng.integers(24, n - 24)); Ts = np.roll(Tt, sh); fl = np.roll(REC, sh); Os = oof(Ts, fl)
    best.append(min(rmse(Os[k], Ts) for k in NOMI))
soglia = float(np.percentile(best, 5)); print("soglia migliore-fra-N (5° pct dei minimi RMSE sotto spostamento):", round(soglia, 2), " mediana", round(float(np.median(best)), 2))
# scelta
cand = sorted(NOMI, key=lambda k: tab[k]["rmse"]); migliore = cand[0]
semplice = {"E1": 7, "E2": 9, "E3": 16, "E4": 14, "E5": 21, "E6": 2, "E7": 4, "E8": 2, "W1": 21, "W2": 9, "W3": 16, "W4": 21, "W5": 9, "W6": 4, "W7": 3, "W8": 14, "X1": 21, "X2": 9, "X3": 21, "X4": 9, "X5": 4, "X6": 2, "X7": 21, "X8": 9}
vicine = [k for k in cand if tab[k]["rmse"] <= tab[migliore]["rmse"] * 1.03]
scelta = min(vicine, key=lambda k: (semplice[k], tab[k]["rmse"]))
print("migliore", migliore, "entro il 3%:", vicine, "-> scelta", scelta)
rob = {"(a) RMSE <= 0.9*R0": tab[scelta]["rmse"] <= 0.9 * tab["R0"]["rmse"], "(b) sotto soglia caso": tab[scelta]["rmse"] < soglia, "(c) falsi allarmi <= 10%": tab[scelta]["falsi_allarmi"] <= 0.10}
print("regole:", rob)
# modello finale su tutto il campione
tr = np.arange(n); Z = prep(tr); st, _ = modello(scelta, Z, tr, tr, Tt, flag); a, b = ols(st, Tt)
_, sc_all = modello(scelta, Z, tr, np.arange(n), Tt, flag); ind = np.clip(a + b * sc_all, 0, 100)
res = {"tabella": tab, "soglia_caso": soglia, "scelta": scelta, "migliore": migliore, "vicine": vicine, "regole": {k: bool(v) for k, v in rob.items()}, "oggi": float(ind[-1]), "data": str(idx[-1].date())}
# pesi/contributi per la scelta (solo se lineare sulle misure)
for nome in (scelta,):
    if nome in ("W1", "W2", "W3", "W8", "W4", "W5"):
        c = {"W1": ALL, "W2": PL["L"] + PL["G"], "W3": PL["L"] + PL["G"] + PL["M"], "W4": ALL, "W5": PL["L"] + PL["G"], "W8": PL["L"] + PL["G"] + PL["K"]}[nome]
        A, y = Z[c].to_numpy(), Tt - Tt.mean()
        wv = np.clip(Ridge(alpha=10, fit_intercept=False).fit(A, y).coef_, 0, None) if nome in ("W4", "W5") else nnls(A, y)[0]
        res["pesi_misure"] = {m: float(x * b) for m, x in zip(c, wv)}; res["contributi_oggi"] = {m: float(Z[m].iloc[-1] * x * b) for m, x in zip(c, wv)}; res["intercetta"] = float(a)
print({k: round(v, 3) for k, v in res.get("pesi_misure", {}).items() if v > 1e-9})
print("OGGI:", round(res["oggi"], 1), " ultimi mesi:", [round(float(x), 1) for x in ind[-6:]])
print("storia (picchi):", {str(i.date()): round(float(v), 0) for i, v in zip(idx, ind) if v >= 85}.__len__(), "mesi >= 85")
res["indice_mensile"] = {str(i.date()): round(float(v), 1) for i, v in zip(idx, ind)}
json.dump(res, open("scratch/salute_economia_esito.json", "w"), indent=1, default=float)
