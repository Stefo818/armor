"""Supplemento (post-hoc, dichiarato): i modelli con 20000 spostamenti invece di 300 (con 300 il p minimo era 1/301 e la correzione di Bonferroni rendeva impossibile passare)."""
import json, numpy as np, sys
from scipy.stats import rankdata
exec(open("scratch/ricerca_10000.py").read().split("# ---------------- segnali")[0])   # calendario, bersagli
RES = json.load(open("scratch/ricerca_10000_esito.json")); rng = np.random.default_rng(77)
bl_all = qtr
for tg in ("T1", "T2", "T3"):
    P = np.load(f"/tmp/pred_{tg}.npy", allow_pickle=True).item(); mk, y_all = MASK[tg], Y[tg]; rows_v = np.where(mk & (yrs >= 2008))[0]; yv = y_all[rows_v]; out = {}
    for k, p in P.items():
        sc = p[rows_v]; ok = np.isfinite(sc)
        if ok.sum() < 500 or yv[ok].sum() < 20: continue
        y_ = yv[ok]; rk_ = rankdata(sc[ok]); n1 = y_.sum(); n0 = len(y_) - n1; obs = (rk_[y_ == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
        offs = rng.integers(250, len(y_) - 250, 20000); idx1 = np.where(y_ == 1)[0]
        nulls = np.array([(rk_[(idx1 + o) % len(y_)].sum() - n1 * (n1 + 1) / 2) / (n1 * n0) for o in offs]); pv = (1 + (nulls >= obs).sum()) / 20001
        out[k] = dict(auc=float(obs), p=float(pv), p_corr=float(min(1, pv * 33)))
    base = RES[tg]["modelli"]
    for k, v in out.items():
        b = base[k]; v.update(ic90=b["ic90"], lift=b["lift"]); v["passa"] = bool(v["auc"] >= 0.60 and v["ic90"] > 0.5 and v["lift"] >= 1.25 and v["p_corr"] < 0.05)
    RES[tg]["modelli_20000"] = out
    pas = [(k, round(v["auc"], 3), round(v["lift"], 2), round(v["ic90"], 2), round(v["p_corr"], 3)) for k, v in sorted(out.items(), key=lambda kv: -kv[1]["auc"]) if v["passa"]]
    print(tg, "modelli che passano con 20000 spostamenti:", len(pas), pas[:12], flush=True)
json.dump(RES, open("scratch/ricerca_10000_esito.json", "w"), indent=1, default=float)
