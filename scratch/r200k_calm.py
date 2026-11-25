"""I modelli migliori addestrati sul vecchio (1932-1989): funzionano anche nei giorni calmi e prima dei picchi dopo periodi calmi?"""
import pickle, json, sys
from r200k_lib import *
from sklearn.linear_model import LogisticRegression
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
D = pickle.load(open("/tmp/r200k_P.pkl", "rb")); cal = D["cal"]; Y = D["Y"]; rows = D["rows"]; N = len(cal); yrs = np.asarray(cal.year); rg = np.random.default_rng(3)
sp = store.load("sp500").dropna(); sp = sp[~sp.index.duplicated()]; C = sp.reindex(cal); Cn = C.to_numpy(float); vol60 = np.log(C).diff().rolling(60).std().to_numpy()
S0 = Setup(cal, C, "P", seed=1); ext = ~S0.MASK["T1"]
peaks = []
for i in range(20, N - 120):
    if ext[i] or Cn[i] < Cn[i - 20:i + 21].max(): continue
    if Cn[i + 1:i + 121].min() / Cn[i] - 1 <= -0.05 and (not peaks or i - peaks[-1] > 20): peaks.append(i)
peaks = np.array(peaks); medv = np.nanmedian(vol60[S0.pr["old"]])
def auc(s, y):
    ok = np.isfinite(s); rk = rankdata(s[ok]); yy = y[ok]; n1 = yy.sum(); return float((rk[yy == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(yy) - n1)))
def pshift(s, y, nsh=10000):
    ok = np.isfinite(s); s = s[ok]; y = y[ok]; rk = rankdata(s).astype(np.float32); n = len(y); n1 = y.sum(); obs = (rk[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * (n - n1)); ge = 0; ar = np.arange(n)
    for c0 in range(0, nsh, 1000):
        offs = rg.integers(n // 10, n - n // 10, 1000); ys = y[(ar[None, :] + offs[:, None]) % n].astype(np.float32); ge += int(((ys @ rk - n1 * (n1 + 1) / 2) / (n1 * (n - n1)) >= obs).sum())
    return (1 + ge) / (nsh + 1)
OUT = {}
for tg, K, alg in (("T1", 30, "logL2_001"), ("T1", 100, "logL2_001"), ("T2", 100, "lda"), ("T2", 100, "logL2_001")):
    y_all = Y[tg]; cand = D["top_old"][tg][:300]; Z = np.column_stack([c[2] for c in cand]); trn = rows[tg]["old"][::2]; yt = y_all[trn]
    Xt = Z[trn]; med = np.nanmedian(Xt, axis=0); med = np.where(np.isnan(med), 0, med); Xt = np.where(np.isnan(Xt), med, Xt); mu, sd = Xt.mean(0), Xt.std(0) + 1e-9
    m = (LogisticRegression(C=0.01, max_iter=200) if alg == "logL2_001" else LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto"))
    Ztr = np.clip((Xt[:, :K] - mu[:K]) / sd[:K], -5, 5); m.fit(Ztr, yt)
    Zall = np.clip((np.where(np.isnan(Z), med, Z)[:, :K] - mu[:K]) / sd[:K], -5, 5); sc = np.full(N, np.nan); sc[rows[tg]["sel"]] = m.predict_proba(Zall[rows[tg]["sel"]])[:, 1]; sc[rows[tg]["ver"]] = m.predict_proba(Zall[rows[tg]["ver"]])[:, 1]
    cut = np.percentile(sc[rows[tg]["sel"]], 90); al = (sc >= cut) & np.isfinite(sc); r_ = {}
    for per in ("sel", "ver"):
        rr = rows[tg][per]; y = y_all[rr]; calm = np.isfinite(vol60[rr]) & (vol60[rr] <= medv); pk = peaks[(yrs[peaks] >= (1992 if per == "sel" else 2008)) & (yrs[peaks] <= (2007 if per == "sel" else 3000))]
        cp = [i for i in pk if np.isfinite(vol60[i - 10]) and vol60[i - 10] <= medv]
        r_[per] = dict(auc=auc(sc[rr], y), auc_vol60=auc(vol60[rr], y), n_calmi=int(calm.sum()), auc_giorni_calmi=auc(sc[rr][calm], y[calm]), p_giorni_calmi=pshift(sc[rr][calm], y[calm]), auc_vol60_giorni_calmi=auc(vol60[rr][calm], y[calm]),
                       eventi_giorni_calmi=float(y[calm].mean()), n_picchi_calmi=len(cp), copertura_picchi_calmi=float(np.mean([al[max(0, i - 10):i + 6].any() for i in cp])) if cp else None, n_picchi=len(pk), copertura_picchi=float(np.mean([al[max(0, i - 10):i + 6].any() for i in pk])))
    OUT[f"{tg}_{alg}_{K}"] = r_; LOG(tg, alg, K, {p: {k: (round(v, 3) if isinstance(v, float) else v) for k, v in x.items()} for p, x in r_.items()})
json.dump(OUT, open("scratch/r200k_calm.json", "w"), indent=1, default=float)
