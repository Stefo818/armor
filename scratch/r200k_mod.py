"""Modelli: P = addestrati su 1932-1989 e provati su 1992-oggi; A = walk-forward dal 2008."""
import sys, pickle, json
from r200k_lib import *
from sklearn.linear_model import LogisticRegression
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, HistGradientBoostingClassifier
G = sys.argv[1]; D = pickle.load(open(f"/tmp/r200k_{G}.pkl", "rb")); cal = D["cal"]; Y = D["Y"]; rows = D["rows"]; N = len(cal)
yrs = np.asarray(cal.year); rg = np.random.default_rng(5)
ALG = {"logL2_001": lambda: LogisticRegression(C=0.01, max_iter=200), "logL2_01": lambda: LogisticRegression(C=0.1, max_iter=200), "logL1": lambda: LogisticRegression(C=0.05, penalty="l1", solver="liblinear"),
       "lda": lambda: LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto"), "nb": lambda: GaussianNB(), "knn50": lambda: KNeighborsClassifier(50),
       "rf": lambda: RandomForestClassifier(100, max_depth=5, min_samples_leaf=20, n_jobs=2, random_state=0), "et": lambda: ExtraTreesClassifier(100, max_depth=6, min_samples_leaf=20, n_jobs=2, random_state=0),
       "hgb2": lambda: HistGradientBoostingClassifier(max_depth=2, max_iter=100, learning_rate=0.05, random_state=0), "hgb3": lambda: HistGradientBoostingClassifier(max_depth=3, max_iter=100, learning_rate=0.05, random_state=0),
       "hgb4": lambda: HistGradientBoostingClassifier(max_depth=4, max_iter=100, learning_rate=0.05, random_state=0)}
KS = (30, 100, 300); NMOD = len(ALG) * len(KS) * 3; OUT = {"n_modelli": NMOD}
def shifts_p(score, y, nsh=20000):
    rk = rankdata(score).astype(np.float32); n = len(y); n1 = y.sum(); obs = (rk[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * (n - n1)); ge = 0; ar = np.arange(n)
    for c0 in range(0, nsh, 1000):
        offs = rg.integers(max(20, n // 10), n - max(20, n // 10), 1000); idx = (ar[None, :] + offs[:, None]) % n; ys = y[idx].astype(np.float32)
        ge += int(((ys @ rk - n1 * (n1 + 1) / 2) / (n1 * (n - n1)) >= obs).sum())
    return float(obs), (1 + ge) / (nsh + 1)
def evalm(p, y, rr):
    sc = p[rr]; ok = np.isfinite(sc)
    if ok.sum() < 300 or y[rr][ok].sum() < 15: return None
    yy = y[rr][ok]; s_ = sc[ok]; obs, pv = shifts_p(s_, yy); al = s_ >= np.percentile(s_, 90)
    return dict(auc=obs, p=pv, p_corr=min(1.0, pv * NMOD / 3), lift=float(yy[al].mean() / yy.mean()))
for tg in ("T1", "T2", "T3"):
    y_all = Y[tg]; mk = np.zeros(N, bool); mk[np.concatenate([rows[tg][k] for k in rows[tg]])] = True
    PRED = {f"{a}_{k}": np.full(N, np.nan) for a in ALG for k in KS}
    if G == "P":
        cand = D["top_old"][tg][:300]; Z = np.column_stack([c[2] for c in cand]); trn = rows[tg]["old"][::2]; yt = y_all[trn]
        Xt = Z[trn]; med = np.nanmedian(Xt, axis=0); med = np.where(np.isnan(med), 0, med); Xt = np.where(np.isnan(Xt), med, Xt); mu, sd = Xt.mean(0), Xt.std(0) + 1e-9
        te = np.concatenate([rows[tg]["sel"], rows[tg]["ver"]]); Xe = np.where(np.isnan(Z[te]), med, Z[te])
        for K in KS:
            Zt = np.clip((Xt[:, :K] - mu[:K]) / sd[:K], -5, 5); Ze = np.clip((Xe[:, :K] - mu[:K]) / sd[:K], -5, 5)
            for a, mkf in ALG.items():
                try: PRED[f"{a}_{K}"][te] = mkf().fit(Zt, yt).predict_proba(Ze)[:, 1]
                except Exception as e: pass
        periodi = {"1992-2007": rows[tg]["sel"], "2008-oggi": rows[tg]["ver"]}
    else:
        cand = D["top_sel"][tg][:300]; Z = np.column_stack([c[2] for c in cand]); mkr = mk
        for Y0 in range(2008, 2027, 2):
            i0 = int(np.where(yrs >= Y0)[0][0]); i1 = int(np.where(yrs >= Y0 + 2)[0][0]) if (yrs >= Y0 + 2).any() else N
            trn = np.where(mkr & (np.arange(N) < i0 - 45))[0][::2]; te = np.arange(i0, i1); yt = y_all[trn]
            Xt = Z[trn]; med = np.nanmedian(Xt, axis=0); med = np.where(np.isnan(med), 0, med); Xt = np.where(np.isnan(Xt), med, Xt); rk = rankdata(Xt, axis=0); n1_ = yt.sum(); n0_ = len(yt) - n1_
            auc_ = (yt @ rk - n1_ * (n1_ + 1) / 2) / (n1_ * n0_); o_ = np.argsort(-np.abs(auc_ - 0.5)); Xe = np.where(np.isnan(Z[te]), med, Z[te]); mu, sd = Xt.mean(0), Xt.std(0) + 1e-9
            for K in KS:
                cols = o_[:K]; Zt = np.clip((Xt[:, cols] - mu[cols]) / sd[cols], -5, 5); Ze = np.clip((Xe[:, cols] - mu[cols]) / sd[cols], -5, 5)
                for a, mkf in ALG.items():
                    try: PRED[f"{a}_{K}"][te] = mkf().fit(Zt, yt).predict_proba(Ze)[:, 1]
                    except Exception as e: pass
        periodi = {"2008-oggi": rows[tg]["ver"]}
    out = {}
    for k, p in PRED.items():
        r_ = {per: evalm(p, y_all, rr) for per, rr in periodi.items()}
        if any(v is None for v in r_.values()): continue
        v = r_["2008-oggi"]; extra = r_.get("1992-2007")
        v["passa"] = bool(v["auc"] >= 0.60 and v["lift"] >= 1.25 and v["p_corr"] < 0.05 and (extra is None or extra["auc"] >= 0.58))
        out[k] = r_ | {"passa": v["passa"]}
    best = sorted(out.items(), key=lambda kv: -kv[1]["2008-oggi"]["auc"])[:5]
    LOG(f"[{G}/{tg}] modelli {len(out)}; passano {sum(v['passa'] for v in out.values())}; migliori:", [(k, round(v["2008-oggi"]["auc"], 3), round(v["2008-oggi"]["lift"], 2), round(v["2008-oggi"]["p_corr"], 2), None if "1992-2007" not in v else round(v["1992-2007"]["auc"], 3)) for k, v in best])
    OUT[tg] = out
json.dump(OUT, open(f"scratch/r200k_mod_{G}.json", "w"), indent=1, default=float); LOG("fatto")
