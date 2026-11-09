import sys, warnings; warnings.filterwarnings("ignore")
sys.path.insert(0, "/home/claude/armor_work/Armor/src")
import numpy as np, pandas as pd
from armor import store
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

sp = store.load("sp500").dropna()
M = sp.resample("ME").last()
def m(sid, how="last"):
    s = store.load(sid).dropna()
    return getattr(s.resample("ME"), how)().reindex(M.index).ffill(limit=2)
pe = m("pe_m"); cape = m("cape_m"); baa = m("baa10y"); nfci = m("nfci"); icsa = m("icsa", "mean")
t3m = m("t10y3m"); dgs10 = m("dgs10"); vix = m("vix"); epu = m("epu", "mean"); aaii = m("aaii_spread", "mean"); skew = m("skew")
eps = M / pe  # utili per azione impliciti (trailing)
F = pd.DataFrame({
  "cape": cape,
  "erp": 100 / pe - dgs10,                 # rendimento utili - BTP10 USA
  "eps_g12": eps.pct_change(12) * 100,     # crescita utili 12 mesi
  "eps_g3": eps.pct_change(3) * 100,
  "baa": baa, "baa_d6": baa - baa.shift(6), # spread credito e allargamento
  "nfci": nfci,
  "claims_d6": (icsa / icsa.rolling(12).min() - 1) * 100,  # sussidi sopra il minimo annuo (segnale recessione)
  "curve": t3m, "curve_min12": t3m.rolling(12).min(),
  "mom12": (M / M.shift(12) - 1) * 100, "sma10": (M / M.rolling(10).mean() - 1) * 100,
  "vix": vix, "epu": epu, "aaii": aaii, "skew": skew,
})
# target
d = sp
def fwd(h):
    r = (M.shift(-h) / M - 1) * 100
    dd = []
    for t in M.index:
        w = d[(d.index > t) & (d.index <= t + pd.DateOffset(months=h))]
        dd.append(np.nan if len(w) < h * 15 else (w.min() / M[t] - 1) * 100)
    return r, pd.Series(dd, M.index)
SETS = {
 "solo mercato (mom, sma, vix)": ["mom12", "sma10", "vix"],
 "fondamentali+macro": ["cape", "erp", "eps_g12", "eps_g3", "baa", "baa_d6", "nfci", "claims_d6", "curve", "curve_min12"],
 "tutto": list(F.columns),
}
out = []
for h in [1, 3, 6, 12]:
    r, dd = fwd(h)
    for tname, y in [("rialzo", (r > 0).astype(float)), ("calo>=10%", (dd <= -10).astype(float))]:
        y = y.where(r.notna())
        for sname, cols in SETS.items():
            X = F[cols]
            ok = X.notna().all(1) & y.notna()
            Xo, yo = X[ok], y[ok]
            for mname in ["logit", "gbm"]:
                P, Y, C = [], [], []
                for yr in range(2000, 2027):
                    te = Xo.index.year == yr
                    if not te.any(): continue
                    cut = pd.Timestamp(f"{yr}-01-01") - pd.DateOffset(months=h)
                    tr = Xo.index < cut
                    if tr.sum() < 120 or yo[tr].nunique() < 2: continue
                    if mname == "logit":
                        sc = StandardScaler().fit(Xo[tr]); mdl = LogisticRegression(C=0.3, max_iter=500).fit(sc.transform(Xo[tr]), yo[tr])
                        p = mdl.predict_proba(sc.transform(Xo[te]))[:, 1]
                    else:
                        mdl = HistGradientBoostingClassifier(max_depth=2, learning_rate=0.05, max_iter=150, min_samples_leaf=30).fit(Xo[tr], yo[tr])
                        p = mdl.predict_proba(Xo[te])[:, 1]
                    P += list(p); Y += list(yo[te]); C += [yo[tr].mean()] * te.sum()
                P, Y, C = map(np.array, (P, Y, C))
                if len(set(Y)) < 2: continue
                bs = np.mean((P - Y) ** 2); bc = np.mean((C - Y) ** 2)
                out.append(dict(h=h, target=tname, set=sname, model=mname, n=len(Y), base=round(Y.mean(), 2), auc=round(roc_auc_score(Y, P), 3), bss=round(1 - bs / bc, 3)))
                print(out[-1], flush=True)
pd.DataFrame(out).to_csv("fund_res.csv", index=False)
